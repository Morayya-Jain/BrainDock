#!/usr/bin/env python3
"""
Quick test to verify the input buffer fix.
This simulates the session start flow to ensure no premature exit.
"""

import time
import sys

print("=" * 60)
print("Testing Input Buffer Fix")
print("=" * 60)

print("\n1️⃣  Simulating wait_for_start()...")
print("Press Enter to start...")
input()

print("\n✓ First input received")
print("Adding delay and flushing buffer...")
time.sleep(0.3)

# Flush stdin
if sys.stdin.isatty():
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        print("✓ Buffer flushed (Unix/Mac)")
    except:
        print("⚠️  Buffer flush not available (Windows)")

print("\n2️⃣  Simulating run_session()...")
print("Press Enter again to stop (should NOT auto-stop)...")

# Start a timer
start = time.time()

# Wait for second input
try:
    input()
    elapsed = time.time() - start
    print(f"\n✓ Second input received after {elapsed:.1f} seconds")
    
    if elapsed < 1.0:
        print("⚠️  WARNING: Input received too quickly!")
        print("   This might indicate the buffer issue still exists.")
    else:
        print("✅ SUCCESS: Buffer is properly cleared!")
        
except KeyboardInterrupt:
    print("\n✓ Ctrl+C works correctly")

print("\n" + "=" * 60)
print("Test completed")
print("=" * 60)
