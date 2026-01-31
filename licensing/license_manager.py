"""
License Manager for BrainDock.

Handles license validation, storage, and verification.
Supports Stripe payments as the activation method.
"""

import json
import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_machine_id() -> str:
    """
    Generate a unique machine identifier for license binding.
    
    Uses multiple sources to create a stable identifier that persists
    across reboots but is unique per machine.
    
    Returns:
        SHA256 hash of combined hardware identifiers (truncated to 32 chars).
    """
    identifiers = []
    
    # Method 1: Try to get MAC address
    try:
        mac = uuid.getnode()
        # Only use if it's a real MAC (not randomly generated)
        if (mac >> 40) % 2 == 0:  # Check multicast bit
            identifiers.append(str(mac))
    except Exception:
        pass
    
    # Method 2: Platform-specific identifiers
    import platform
    import sys
    
    try:
        if sys.platform == "darwin":
            # macOS: Use hardware UUID
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'IOPlatformUUID' in line:
                        uuid_part = line.split('"')[-2]
                        identifiers.append(uuid_part)
                        break
        elif sys.platform == "win32":
            # Windows: Use machine GUID from registry
            import subprocess
            result = subprocess.run(
                ["reg", "query", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography", "/v", "MachineGuid"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'MachineGuid' in line:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            identifiers.append(parts[-1])
                        break
    except Exception:
        pass
    
    # Method 3: Fallback to platform info (less unique but always available)
    identifiers.append(platform.node())
    identifiers.append(platform.machine())
    
    # Combine all identifiers and hash
    combined = "|".join(identifiers)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


class LicenseManager:
    """
    Manages BrainDock license state.
    
    Handles checking license validity, saving license data,
    and verifying Stripe payments.
    """
    
    # License types
    LICENSE_TYPE_STRIPE = "stripe_payment"
    LICENSE_TYPE_PROMO = "promo_code"
    
    def __init__(self, license_file: Path):
        """
        Initialize the license manager.
        
        Args:
            license_file: Path to the license data JSON file.
        """
        self.license_file = license_file
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """
        Load license data from JSON file.
        
        Returns:
            Dict containing license data.
        """
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r') as f:
                    data = json.load(f)
                    # Verify checksum if present
                    if not self._verify_checksum(data):
                        logger.warning("License file checksum mismatch - possible tampering")
                        return self._default_data()
                    logger.debug(f"Loaded license data: licensed={data.get('licensed', False)}")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load license data: {e}")
        
        return self._default_data()
    
    def _default_data(self) -> Dict[str, Any]:
        """Return default license data for unlicensed state."""
        return {
            "licensed": False,
            "license_type": None,
            "stripe_session_id": None,
            "stripe_payment_intent": None,
            "activated_at": None,
            "email": None,
            "machine_id": None,
            "checksum": None
        }
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """
        Calculate checksum for license data integrity.
        
        Uses full SHA256 hash (not truncated) for security.
        
        Args:
            data: License data dictionary.
            
        Returns:
            Full SHA256 checksum string (64 characters).
        """
        # Create a copy without the checksum field
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        # Sort keys for consistent hashing
        data_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()  # Full hash, not truncated
    
    def _verify_checksum(self, data: Dict[str, Any]) -> bool:
        """
        Verify the checksum and machine binding of license data.
        
        Security: Requires checksum to be present. Missing checksum is treated
        as tampering (prevents bypass by removing checksum field).
        
        Also verifies machine binding if present - license won't work on
        a different machine than it was activated on.
        
        Args:
            data: License data dictionary.
            
        Returns:
            True if checksum is valid and machine matches, False otherwise.
        """
        stored_checksum = data.get("checksum")
        
        # Security: Require checksum for licensed entries
        # Only allow missing checksum for unlicensed (default) data
        if not stored_checksum:
            if data.get("licensed", False):
                logger.warning("License file missing checksum - possible tampering")
                return False
            return True  # Unlicensed data doesn't need checksum
        
        # Verify checksum (support both old truncated and new full checksums)
        calculated = self._calculate_checksum(data)
        # Old format used 16-char truncated hash, new format uses full 64-char hash
        if stored_checksum != calculated and stored_checksum != calculated[:16]:
            logger.warning("License checksum mismatch - possible tampering")
            return False
        
        # Verify machine binding if present
        stored_machine_id = data.get("machine_id")
        if stored_machine_id:
            current_machine_id = _get_machine_id()
            if stored_machine_id != current_machine_id:
                logger.warning("License machine ID mismatch - license may have been copied")
                return False
        
        return True
    
    def _save_data(self) -> None:
        """Save license data to JSON file with checksum."""
        try:
            # Ensure parent directory exists
            self.license_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add checksum before saving
            self.data["checksum"] = self._calculate_checksum(self.data)
            
            with open(self.license_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.debug("Saved license data")
        except IOError as e:
            logger.error(f"Failed to save license data: {e}")
    
    def is_licensed(self) -> bool:
        """
        Check if the app is licensed.
        
        Returns:
            True if licensed, False otherwise.
        """
        return self.data.get("licensed", False)
    
    def get_license_type(self) -> Optional[str]:
        """
        Get the type of license activation.
        
        Returns:
            License type string or None if not licensed.
        """
        return self.data.get("license_type")
    
    def get_license_info(self) -> Dict[str, Any]:
        """
        Get license information for display.
        
        Returns:
            Dict with license details.
        """
        return {
            "licensed": self.data.get("licensed", False),
            "type": self.data.get("license_type"),
            "activated_at": self.data.get("activated_at"),
            "email": self.data.get("email")
        }
    
    def activate_with_stripe(
        self,
        session_id: str,
        payment_intent: Optional[str] = None,
        email: Optional[str] = None
    ) -> bool:
        """
        Activate license after successful Stripe payment.
        
        Binds the license to the current machine to prevent copying.
        
        Args:
            session_id: Stripe Checkout session ID.
            payment_intent: Optional Stripe payment intent ID.
            email: Optional customer email from Stripe.
            
        Returns:
            True if activation successful.
        """
        self.data = {
            "licensed": True,
            "license_type": self.LICENSE_TYPE_STRIPE,
            "stripe_session_id": session_id,
            "stripe_payment_intent": payment_intent,
            "activated_at": datetime.now().isoformat(),
            "email": email,
            "machine_id": _get_machine_id(),  # Bind to this machine
            "checksum": None
        }
        self._save_data()
        logger.info(f"License activated via Stripe payment (session: {session_id[:20] if session_id else 'unknown'}...)")
        return True
    
    def activate_with_promo(
        self,
        session_id: str,
        promo_code: str,
        email: Optional[str] = None
    ) -> bool:
        """
        Activate license after successful promo code redemption via Stripe.
        
        Binds the license to the current machine to prevent copying.
        
        Args:
            session_id: Stripe Checkout session ID.
            promo_code: The promo code that was used.
            email: Optional customer email from Stripe.
            
        Returns:
            True if activation successful.
        """
        self.data = {
            "licensed": True,
            "license_type": self.LICENSE_TYPE_PROMO,
            "stripe_session_id": session_id,
            "stripe_payment_intent": None,
            "promo_code": promo_code,  # Store the promo code used
            "activated_at": datetime.now().isoformat(),
            "email": email,
            "machine_id": _get_machine_id(),  # Bind to this machine
            "checksum": None
        }
        self._save_data()
        logger.info("License activated via promo code")
        return True
    
    def revoke_license(self) -> None:
        """Revoke the current license (reset to unlicensed state)."""
        self.data = self._default_data()
        self._save_data()
        logger.info("License revoked")
    
    def get_activation_date(self) -> Optional[datetime]:
        """
        Get the date when the license was activated.
        
        Returns:
            Datetime of activation or None if not licensed.
        """
        activated_at = self.data.get("activated_at")
        if activated_at:
            try:
                return datetime.fromisoformat(activated_at)
            except ValueError:
                pass
        return None


# Global instance for easy access (thread-safe singleton)
_license_manager_instance: Optional[LicenseManager] = None
_license_manager_lock = __import__('threading').Lock()


def get_license_manager() -> LicenseManager:
    """
    Get the global LicenseManager instance.
    
    Thread-safe: Uses double-check locking pattern to prevent
    race conditions during initialization.
    
    Returns:
        Singleton LicenseManager instance.
    """
    global _license_manager_instance
    if _license_manager_instance is None:
        with _license_manager_lock:
            # Double-check after acquiring lock
            if _license_manager_instance is None:
                # Import config here to avoid circular imports
                import config
                _license_manager_instance = LicenseManager(
                    license_file=config.LICENSE_FILE
                )
    return _license_manager_instance


def reset_license_manager() -> None:
    """Reset the global license manager instance (useful for testing)."""
    global _license_manager_instance
    _license_manager_instance = None
