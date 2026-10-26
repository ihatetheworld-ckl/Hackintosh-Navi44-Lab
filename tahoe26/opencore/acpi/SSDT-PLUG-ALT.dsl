/*
 * Intel ACPI Component Architecture
 * AML/ASL+ Disassembler / Template for Alder Lake XCPM Power Management
 *
 * Target Hardware: Intel Core i5-12600KF on Maxsun MS-Terminator B760M D5
 * Confirmed ACPI CPU Table: SSD1\CpuRef\CpuSsdt\00003000 (\_SB.PR00)
 * Purpose: Attach plugin-type = 1 to the primary processor object (\_SB.PR00)
 *          for macOS 26 Tahoe XCPM power management.
 */
DefinitionBlock ("", "SSDT", 2, "TAHOE", "PLUG-ALT", 0x00001000)
{
    External (\_SB_.PR00, ProcessorObj)

    Scope (\_SB.PR00)
    {
        Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
        {
            If ((Arg2 == Zero))
            {
                Return (Buffer (One)
                {
                     0x03                                             // .
                })
            }

            Return (Package (0x02)
            {
                "plugin-type", 
                One
            })
        }
    }
}
