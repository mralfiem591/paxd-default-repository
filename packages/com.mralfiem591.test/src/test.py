print("If you see this, PaxD's test package was installed successfully!")

print("Testing argv...")
import sys
print(f"Arguments passed to test package: {sys.argv}")

print("Testing SDK...")

import paxd_sdk as sdk # type: ignore # import PaxD SDK
if not sdk.SDKDetails().AssertVersion("1.2.0"):
    print("The SDK test section of this package requires PaxD SDK 1.2.0 or later. Please update your SDK.")

sdk.SDKDetails.PrintInfo() # print SDK info