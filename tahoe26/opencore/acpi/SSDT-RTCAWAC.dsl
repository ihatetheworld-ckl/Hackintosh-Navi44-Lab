/*
 * Disable AWAC ( ACPI000E ) and Force Legacy RTC on Darwin
 *
 * Target Hardware: Maxsun MS-Terminator B760M D5 (Intel 700-series B760 PCH)
 * Purpose: Prevent macOS 26 Tahoe kernel hang waiting on ACPI000E System Timer
 *          when STAS variable prevents RTC from enabling. Only active under _OSI("Darwin").
 */
DefinitionBlock ("", "SSDT", 2, "TAHOE", "RTCAWAC", 0x00001000)
{
    External (STAS, IntObj)

    Scope (\)
    {
        Method (_INI, 0, NotSerialized)  // _INI: Initialize
        {
            If (_OSI ("Darwin"))
            {
                STAS = One
            }
        }
    }
}
