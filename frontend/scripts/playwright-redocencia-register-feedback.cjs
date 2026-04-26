const { chromium } = require('playwright')

const APP_URL = process.env.APP_URL || 'http://localhost:5173'
const email = `redocencia${Date.now()}@mailinator.com`

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })

  try {
    await page.goto(`${APP_URL}/cadastro`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector('input[type="email"]', { timeout: 30000 })

    const inputs = page.locator('input')
    await inputs.nth(0).fill('Teste Supabase')
    await inputs.nth(1).fill(email)
    await inputs.nth(2).fill(`teste${Date.now()}`)
    await inputs.nth(3).fill('Redocencia!123')
    await page.click('button[type="submit"]')

    await page.waitForTimeout(5000)

    const errorText = (await page.locator('.form-error').count())
      ? await page.locator('.form-error').innerText()
      : null
    const successText = (await page.locator('.form-success').count())
      ? await page.locator('.form-success').innerText()
      : null

    console.log(JSON.stringify({ url: page.url(), email, errorText, successText }))
  } catch (error) {
    console.error('PLAYWRIGHT_ERROR=' + error.stack)
  } finally {
    await browser.close()
  }
})()
