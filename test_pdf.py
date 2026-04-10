import asyncio
from playwright.async_api import async_playwright
import newsletter

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Test standard HTML
        html_url = "https://example.com"
        print(f"Testing HTML: {html_url}")
        text, final = await newsletter.extract_text_from_url(page, html_url)
        print(f"Final URL: {final}")
        print(f"Extracted: {text[:100]}...\n")
        
        # Test PDF (ArXiv paper)
        pdf_url = "https://arxiv.org/pdf/1706.03762.pdf"
        print(f"Testing PDF: {pdf_url}")
        text, final = await newsletter.extract_text_from_url(page, pdf_url)
        print(f"Final URL: {final}")
        print(f"Extracted: {text[:100]}...\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
