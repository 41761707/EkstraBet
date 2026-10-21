import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SettleCouponsPanel } from "@/components/admin/SettleCouponsPanel";
import {
  SETTLE_COUPONS_BUTTON,
  SETTLE_COUPONS_DESCRIPTION,
  SETTLE_COUPONS_TITLE,
} from "@/components/admin/settleCouponsModel";

describe("SettleCouponsPanel", () => {
  it("offers the settle action before a click", () => {
    const html = renderToStaticMarkup(<SettleCouponsPanel />);

    expect(html).toContain(SETTLE_COUPONS_TITLE);
    expect(html).toContain(SETTLE_COUPONS_DESCRIPTION);
    expect(html).toContain(SETTLE_COUPONS_BUTTON);
    expect(html).not.toContain("Rozliczanie…");
    expect(html).not.toContain("password");
  });
});
