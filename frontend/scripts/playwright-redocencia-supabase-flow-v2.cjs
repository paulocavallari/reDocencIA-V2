const { chromium } = require('playwright')

const APP_URL = process.env.APP_URL || 'http://localhost:5173'
const inbox = `redocencia${Date.now()}`
const email = `${inbox}@mailinator.com`
const username = `teste${Date.now()}`
const password = 'Redocencia!123'

;(async () => {
  const browser = await chromium.launch({ headless: true, slowMo: 50 })
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })

  try {
    console.log('Using test email:', email)

    await page.goto(`${APP_URL}/cadastro`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector('input[type="email"]', { timeout: 30000 })
    const inputs = page.locator('input')
    await inputs.nth(0).fill('Teste Supabase')
    await inputs.nth(1).fill(email)
    await inputs.nth(2).fill(username)
    await inputs.nth(3).fill(password)
    await page.click('button[type="submit"]')

    await page.waitForTimeout(4000)
    const formError = (await page.locator('.form-error').count())
      ? await page.locator('.form-error').innerText()
      : null
    const bodyAfterRegister = (await page.locator('body').innerText()).slice(0, 2000)
    console.log('REGISTER_RESULT=' + JSON.stringify({ url: page.url(), formError, bodyAfterRegister }))

    await page.goto(`https://www.mailinator.com/v4/public/inboxes.jsp?to=${inbox}`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    })
    await page.waitForTimeout(12000)

    const pageInfo = {
      url: page.url(),
      title: await page.title(),
      body: (await page.locator('body').innerText()).slice(0, 2000),
      buttons: await page
        .locator('button')
        .evaluateAll((els) => els.map((el) => (el.textContent || '').trim()).filter(Boolean).slice(0, 40)),
      links: await page
        .locator('a')
        .evaluateAll((els) => els.map((el) => ({ text: (el.textContent || '').trim(), href: el.href || null })).filter((item) => item.text || item.href).slice(0, 40)),
    }
    console.log('MAILINATOR_INFO=' + JSON.stringify(pageInfo))
  } catch (error) {
    console.error('PLAYWRIGHT_ERROR=' + error.stack)
  } finally {
    await page.screenshot({ path: 'c:/tmp/playwright-redocencia-supabase-flow-v2.png', fullPage: true }).catch(() => {})
    await browser.close()
  }
})()
