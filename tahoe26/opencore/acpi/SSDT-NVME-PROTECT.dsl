/*
 * Windows Primary NVMe Protection SSDT (Optional Software Isolation for Gate C)
 *
 * Target Hardware: WD_BLACK SN850X 2000GB
 * Confirmed Topology: PCI\VEN_8086&DEV_464D (0,6,0) -> Bus 4 PCI\VEN_15B7&DEV_5030 (4,0,0)
 *
 * Purpose: When enabled during macOS 26 Tahoe installation (if physical removal of the
 *          Windows M.2 SSD is inconvenient), this SSDT injects class-code/IOName override
 *          ONLY under Darwin (_OSI("Darwin")) so IONVMeFamily ignores the Windows SSD,
 *          making accidental formatting in Disk Utility impossible while leaving Windows untouched.
 */
DefinitionBlock ("", "SSDT", 2, "TAHOE", "NVMEPROT", 0x00001000)
{
    External (\_SB_.PC00.PEG1, DeviceObj)
    External (\_SB_.PC00.PEG1.PEGP, DeviceObj)

    Scope (\_SB.PC00.PEG1.PEGP)
    {
        Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
        {
            If ((!_OSI ("Darwin") || (Arg2 == Zero)))
            {
                Return (Buffer (One)
                {
                     0x03                                             // .
                })
            }

            Return (Package (0x04)
            {
                "name", 
                Buffer (0x0F)
                {
                    "#disabled-nvme"
                }, 
                "class-code", 
                Buffer (0x04)
                {
                     0xFF, 0xFF, 0xFF, 0xFF                           // ....
                }
            })
        }
    }
}
