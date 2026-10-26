/*
 * Fake Embedded Controller (EC) and USB Power Injection (USBX)
 *
 * Target Hardware: Maxsun MS-Terminator B760M D5 (BIOS E1.5D)
 * Confirmed LPC Bridge: PCI\VEN_8086&DEV_7A06 at (0,31,0) -> \_SB.PC00.LPCB
 * Purpose:
 *   1. Provide a desktop-compatible EC device for AppleACPIEC matching in macOS 26 Tahoe.
 *   2. Provide USBX power properties for MacPro7,1 SMBIOS USB current limits.
 */
DefinitionBlock ("", "SSDT", 2, "TAHOE", "EC-USBX", 0x00001000)
{
    External (\_SB_.PC00.LPCB, DeviceObj)

    Scope (\_SB.PC00.LPCB)
    {
        Device (EC)
        {
            Name (_HID, "ACID0001")  // _HID: Hardware ID
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
    }

    Scope (\_SB)
    {
        Device (USBX)
        {
            Name (_ADR, Zero)  // _ADR: Address
            Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
            {
                If ((Arg2 == Zero))
                {
                    Return (Buffer (One)
                    {
                         0x03                                             // .
                    })
                }

                Return (Package (0x08)
                {
                    "kUSBSleepPortCurrentLimit", 
                    0x0834, 
                    "kUSBSleepPowerSupply", 
                    0x13EC, 
                    "kUSBWakePortCurrentLimit", 
                    0x0834, 
                    "kUSBWakePowerSupply", 
                    0x13EC
                })
            }

            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
    }
}
