import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("auditor creates, edits rich text, finalizes, prints and reopens report",async({page})=>{
  await page.goto("/");await page.evaluate(()=>localStorage.setItem("ains-synthetic-role","auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001");
  await page.getByRole("button",{name:"Draft report",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Independent AML test report",level:1})).toBeVisible();
  await page.getByRole("textbox",{name:"Scope",exact:true}).fill("Synthetic human scope");
  await page.getByRole("textbox",{name:"Scope",exact:true}).press("ControlOrMeta+A");
  await page.getByRole("button",{name:"Bold in Scope",exact:true}).click();
  await page.getByLabel("Finding AML-BD-001",{exact:true}).fill("Synthetic human finding");
  await page.getByRole("button",{name:"Save draft",exact:true}).click();
  await expect(page.getByRole("status").filter({hasText:"Draft saved."})).toBeVisible();
  await page.reload();await expect(page.getByRole("textbox",{name:"Scope",exact:true})).toHaveText("Synthetic human scope");
  await expect(page.getByLabel("Finding AML-BD-001",{exact:true})).toHaveValue("Synthetic human finding");
  expect((await new AxeBuilder({page}).exclude("nextjs-portal").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze()).violations).toEqual([]);
  await page.getByRole("button",{name:"Finalize report",exact:true}).click();
  await page.getByRole("checkbox").check();await page.getByRole("button",{name:"Confirm finalization"}).click();
  await expect(page.getByRole("button",{name:"Reopen report"})).toBeVisible();
  await expect(page.getByRole("textbox",{name:"Scope",exact:true})).toHaveCount(0);
  await page.getByRole("link",{name:"Print view",exact:true}).click();
  await expect(page.getByRole("button",{name:"Print / Save PDF"})).toBeVisible();
  await page.emulateMedia({media:"print"});await expect(page.locator(".report-print")).toBeVisible();await expect(page.locator(".report-controls").first()).toBeHidden();
  await page.emulateMedia({media:"screen"});await page.goto(page.url().replace(/\/print$/,""));
  await page.getByRole("button",{name:"Reopen report"}).click();await expect(page.getByRole("textbox",{name:"Scope",exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("client has no Reports navigation and report routes are blocked",async({page})=>{
  for(const path of ["/auditor/reports","/auditor/reports/synthetic","/auditor/reports/synthetic/print"]){await page.goto(path);await expect(page).toHaveURL(/\/$/);await expect(page.getByRole("link",{name:"Reports",exact:true})).toHaveCount(0);await expect(page.locator(".report-print")).toHaveCount(0);}
});
