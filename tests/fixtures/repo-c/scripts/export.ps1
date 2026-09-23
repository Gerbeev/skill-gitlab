# Reference-only fixture. The engine never executes this file.
$query = "SELECT * FROM reporting.daily_report"
Write-Output $query
