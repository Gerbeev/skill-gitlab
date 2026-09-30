from __future__ import annotations

import unittest
from pathlib import Path

from mr_impact.index.adapters.csharp import CSharpAdapter
from mr_impact.readers import claims

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-repo" / "csharp"


class CSharpAdapterTests(unittest.TestCase):
    def test_csproj_references(self) -> None:
        text = (FIXTURE / "Payments.csproj").read_text(encoding="utf-8")
        symbols, edges, _ = CSharpAdapter().analyze("csharp/Payments.csproj", text)
        self.assertTrue(any(s.kind == "csharp_project" for s in symbols))
        targets = {(e.edge_type, e.target) for e in edges}
        self.assertIn(("package_reference", "Acme.Ledger.Client"), targets)
        self.assertIn(("project_reference", "../Core/Core.csproj"), targets)

    def test_cs_source(self) -> None:
        path = FIXTURE / "PaymentService.cs"
        text = path.read_text(encoding="utf-8")
        rel = "csharp/PaymentService.cs"
        symbols, edges, notes = CSharpAdapter().analyze(rel, text)
        names = {s.name for s in symbols}
        self.assertIn("PaymentService", names)
        self.assertIn("Payments", names)

        using_edges = {e.target for e in edges if e.edge_type == "csharp_using"}
        self.assertIn("Acme.Ledger.Client", using_edges)

        if claims(path) is None:
            self.assertTrue(any("regex-fallback" in n for n in notes))
        else:
            self.assertTrue(any("tree-sitter" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
