$Path = "[PATH_TO_INFO_FILES]"
$Name=$env:COMPUTERNAME
$InfoFile = $Path + $Name + "_info.txt"
$NetFile = $Path + $Name + "_net.txt"
$MonFile = $Path + $Name + "_mon.txt"
$SoftFile = $Path + $Name + "_soft.txt"
$HDDFile = $Path + $Name + "_hdd.txt"
$RAMFile = $Path + $Name + "_ram.txt"

Get-ComputerInfo | ConvertTo-Json | Out-File $InfoFile
$IP=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex (Get-NetAdapter | Where-Object Status -eq "Up").InterfaceIndex).IPAddress
$MASK=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex (Get-NetAdapter | Where-Object Status -eq "Up").InterfaceIndex).PrefixLength

Get-NetIPAddress -AddressFamily IPv4 |  Where-Object {$_.InterfaceAlias -notmatch 'vEthernet'} | Select-Object IPAddress, PrefixLength | ConvertTo-Json | Out-File $NetFile

$MonList = @(Get-CimInstance -Namespace "root\wmi" -ClassName WmiMonitorID | ForEach-Object -Begin { $i = 0 } -Process { $i = $i +1
    [PSCustomObject]@{
        Manufacturer = [System.Text.Encoding]::ASCII.GetString($_.ManufacturerName).Trim("`0")
        Model        = [System.Text.Encoding]::ASCII.GetString($_.UserFriendlyName).Trim("`0")
        SerialNumber = [System.Text.Encoding]::ASCII.GetString($_.SerialNumberID).Trim("`0")
        Year         = $_.YearOfManufacture
        Active       = $_.Active
        Count        = $i
    } 
})
$EmptyMon = @([PSCustomObject]@{Count = "-1"; Model = "None"})
$MonList += $EmptyMon

$MonList | ConvertTo-Json | Out-File $MonFile

Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*, HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Select-Object DisplayName, DisplayVersion, Publisher | Where-Object { $_.DisplayName } | ConvertTo-Json | Out-File $SoftFile

$EmptyDev = @([PSCustomObject]@{DeviceId = "-1"})
$HddList = (Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, Manufacturer, Size, OperationalStatus, SerialNumber, BusType)
$HddList += $EmptyDev

$HddList | ConvertTo-Json | Out-File $HDDFile

$EmptyRam = @([PSCustomObject]@{DeviceLocator = "None"; GB = 0})
$RamList = [PSCustomObject]@(Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Manufacturer, PartNumber, SerialNumber, @{Name="GB";Expression={$_.Capacity / 1GB}}, Speed, ConfiguredVoltage)
$RamList += $EmptyRam
$RamList | ConvertTo-Json | Out-File $RAMFile
