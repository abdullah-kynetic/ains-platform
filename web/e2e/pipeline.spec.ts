import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("auditor can move a synthetic engagement without finalizing a report", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await page.goto("/auditor/pipeline");

  await expect(
    page.getByRole("heading", { name: "Audit pipeline", level: 1 }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic preview", { exact: true })).toBeVisible();

  const stageSelect = page.getByLabel(
    "Move Example Securities LLC (synthetic) to stage",
  );
  await stageSelect.selectOption("auditor_review");
  await expect(
    page.getByRole("region", { name: "Auditor review" }).getByText(
      "Example Securities LLC (synthetic)",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "No report was signed or finalized",
  );

  expect(
    (
      await new AxeBuilder({ page })
        .exclude("nextjs-portal")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});
