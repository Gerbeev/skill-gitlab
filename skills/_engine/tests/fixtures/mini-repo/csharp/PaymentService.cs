using System;

namespace Payments;

public class PaymentService
{
    public bool Reconcile()
    {
        const string sql = "BEGIN payment_pkg.run; END;";
        return Execute(sql);
    }

    private static bool Execute(string sql) => !string.IsNullOrEmpty(sql);
}
