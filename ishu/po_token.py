# ishu/po_token.py
import os
import json
import subprocess
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class POTokenGenerator:
    def __init__(self):
        self.token_cache = {}
        self.script_path = self._create_extractor_script()
    
    def _create_extractor_script(self):
        """PO token extractor script create karo"""
        script_content = '''
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

async function getToken(videoId) {
    try {
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        await page.goto(`https://www.youtube.com/watch?v=${videoId}`, {
            waitUntil: 'networkidle2',
            timeout: 30000
        });
        
        const poToken = await page.evaluate(() => {
            return window.ytcfg?.get('PO_TOKEN') || null;
        });
        
        await browser.close();
        
        console.log(JSON.stringify({ poToken: poToken }));
    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
    }
}

getToken(process.argv[2]);
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script_content)
            return f.name
    
    def get_token(self, video_id: str) -> Optional[str]:
        """PO Token fetch karo"""
        if video_id in self.token_cache:
            return self.token_cache[video_id]
        
        try:
            result = subprocess.run(
                ['node', self.script_path, video_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('poToken'):
                    self.token_cache[video_id] = data['poToken']
                    logger.info(f"✅ PO Token generated for {video_id}")
                    return data['poToken']
                else:
                    logger.warning(f"⚠️ No PO Token in response for {video_id}")
            else:
                logger.warning(f"⚠️ PO Token generation failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ PO Token error: {e}")
        
        return None

# Singleton instance
po_token_gen = POTokenGenerator()
