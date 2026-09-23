namespace Bank.Reporting;

public class ReportClient
{
    public string ReadExposure()
    {
        return "SELECT exposure FROM risk.daily_exposure";
    }
}
