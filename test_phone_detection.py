#!/usr/bin/env python3
"""
Test script to verify the phone detection fix.

This script helps you test that the system correctly distinguishes between:
1. Active phone usage (should detect)
2. Passive phone presence (should NOT detect)
"""

import sys
import os
from pathlib import Path
import cv2
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from camera.vision_detector import VisionDetector
from dotenv import load_dotenv
import config

# Load environment
load_dotenv()

print("═══════════════════════════════════════════════════════")
print("🧪 Phone Detection Test - Active Usage Only")
print("═══════════════════════════════════════════════════════\n")

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ No API key found in .env file")
    print("   Please add: OPENAI_API_KEY=your-key-here")
    sys.exit(1)

print("✓ API key found\n")

# Initialize detector
print("Initializing Vision Detector...")
try:
    detector = VisionDetector(api_key=api_key)
    print("✓ Vision detector initialized\n")
except Exception as e:
    print(f"❌ Failed to initialize detector: {e}")
    sys.exit(1)

# Open camera
print("Opening camera...")
cap = cv2.VideoCapture(config.CAMERA_INDEX)

if not cap.isOpened():
    print("❌ Failed to open camera")
    sys.exit(1)

print("✓ Camera opened\n")

print("═══════════════════════════════════════════════════════")
print("📋 Test Scenarios")
print("═══════════════════════════════════════════════════════")
print("\nTest each scenario for 5-10 seconds:\n")
print("1. 📱 Phone on desk + looking at computer")
print("   Expected: phone_visible = FALSE\n")
print("2. 📱 Phone on desk + looking DOWN at it + screen ON")
print("   Expected: phone_visible = TRUE\n")
print("3. 📱 Phone in hands + looking at it + screen ON")
print("   Expected: phone_visible = TRUE\n")
print("4. 📱 Phone anywhere + screen OFF")
print("   Expected: phone_visible = FALSE\n")
print("5. 📱 Phone in hands + looking away")
print("   Expected: phone_visible = FALSE\n")
print("KEY: Position doesn't matter - it's attention + screen state!")
print("═══════════════════════════════════════════════════════")
print("\nPress Ctrl+C to stop testing\n")

try:
    frame_count = 0
    last_detection_time = 0
    detection_interval = 3  # Test every 3 seconds
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame")
            break
        
        # Show camera feed
        cv2.imshow("Phone Detection Test - Press ESC to quit", frame)
        
        # Test detection every N seconds
        current_time = time.time()
        if current_time - last_detection_time >= detection_interval:
            print(f"\n⏱️  Testing at {time.strftime('%H:%M:%S')}...")
            
            try:
                # Analyze frame
                result = detector.analyze_frame(frame, use_cache=False)
                
                # Print results
                print("─" * 55)
                print(f"  Person Present:   {result['person_present']}")
                print(f"  Phone Visible:    {result['phone_visible']}")
                print(f"  Phone Confidence: {result['phone_confidence']:.2f}")
                print(f"  Distraction Type: {result['distraction_type']}")
                print(f"  Description:      {result['description']}")
                print("─" * 55)
                
                # Interpretation
                if result['phone_visible']:
                    print("  ✅ DETECTED: Active phone usage")
                    if result['phone_confidence'] > 0.7:
                        print("  💪 High confidence - clear phone usage")
                    else:
                        print("  ⚠️  Moderate confidence - possible phone usage")
                else:
                    print("  ✓ NO DETECTION: Not actively using phone")
                
            except Exception as e:
                print(f"  ❌ Error during detection: {e}")
            
            last_detection_time = current_time
        
        # Check for quit
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            break
        elif key == ord('q'):
            break
        
        frame_count += 1

except KeyboardInterrupt:
    print("\n\n✓ Test stopped by user")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("\n═══════════════════════════════════════════════════════")
    print("Test completed")
    print("═══════════════════════════════════════════════════════")
    print("\n✅ If the detection worked correctly:")
    print("   - Phone on desk + looking at computer: phone_visible = False")
    print("   - Phone on desk + looking at it + screen ON: phone_visible = True")
    print("   - Position doesn't matter - it's attention + screen state!")
    print("\n❌ If detection wasn't accurate:")
    print("   - Try adjusting PHONE_CONFIDENCE_THRESHOLD in config.py")
    print("   - Ensure good lighting for better AI vision")
    print("   - Make attention clear (look directly at phone or away)")
    print("   - Ensure phone screen brightness is visible to camera")
    print()
