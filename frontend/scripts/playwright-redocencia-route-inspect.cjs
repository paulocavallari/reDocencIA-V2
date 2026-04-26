const { chromium } = require('playwright')

const APP_URL = process.env.APP_URL || 'http://localhost:5173'

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })

  try {
    await page.goto(`${APP_URL}/cadastro`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(5000)
    const inputs = await page.locator('input').evaluateAll((els) =>
      els.map((el) => ({
        type: el.type,
        name: el.name,
        placeholder: el.placeholder,
        value: el.value,
      }))
    )
    const buttons = await page.locator('button').evaluateAll((els) =>
      els.map((el) => (el.textContent || '').trim()).filter(Boolean)
    )
    console.log('URL=' + page.url())
    console.log('TITLE=' + (await page.title()))
    console.log('INPUTS=' + JSON.stringify(inputs))
    console.log('BUTTONS=' + JSON.stringify(buttons))
    console.log('BODY=' + JSON.stringify((await page.locator('body').innerText()).slice(0, 2000)))
  } catch (error) {
    console.error('PLAYWRIGHT_ERROR=' + error.stack)
  } finally {
    await page.screenshot({ path: 'c:/tmp/playwright-redocencia-route-inspect-v2.png', fullPage: true }).catch(() => {})
    await browser.close()
  }
})()
