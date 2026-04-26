const { chromium } = require('playwright')

const APP_URL = process.env.APP_URL || 'http://localhost:5173'

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })

  try {
    const results = []
    for (const path of ['/login', '/cadastro']) {
      await page.goto(`${APP_URL}${path}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
      await page.waitForTimeout(1500)
      const title = await page.title()
      const body = (await page.locator('body').innerText()).slice(0, 500)
      results.push({ path, title, body })
    }
    console.log(JSON.stringify(results))
  } catch (error) {
    console.error('PLAYWRIGHT_ERROR=' + error.stack)
  } finally {
    await browser.close()
  }
})()
