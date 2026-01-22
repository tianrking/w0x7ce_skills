import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { launchChrome, getPageSession, typeText, evaluate, sleep, type ChromeSession } from './cdp.ts';

// LinkedIn URLs
const LINKEDIN_FEED_URL = 'https://www.linkedin.com/feed/';
const LINKEDIN_DOMAIN = 'linkedin.com';

// Multi-language selectors for "Start a post" button
const START_POST_SELECTORS = [
  'button[aria-label*="Start a post"]',
  'button[aria-label*="开始发帖"]',
  'button[aria-label*="開始發貼"]',
  'div.share-box-feed-entry__trigger',
  'button[data-control-name="share_box"]',
  'span[aria-label*="Start a post"]',
];

// Multi-language selectors for post editor
const EDITOR_SELECTORS = [
  'div[contenteditable="true"][role="textbox"]',
  'div[role="textbox"]',
  'div.ql-editor',
  '[data-artdeco-is-focused="true"]',
];

// Multi-language selectors for post button
const POST_BUTTON_SELECTORS = [
  'button[aria-label*="Post"]',
  'button[aria-label*="发布"]',
  'button[aria-label*="發佈"]',
  'button[data-control-name="share.post"]',
  'button.share-actions__primary-action',
];

interface PostOptions {
  text?: string;
  images?: string[];
  submit?: boolean;
  profileDir?: string;
}

async function waitForElement(session: ChromeSession, selectors: string[], timeoutMs = 30_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const result = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
      expression: `
        (function() {
          const selectors = ${JSON.stringify(selectors)};
          for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (el && el.offsetParent !== null) return true;
          }
          return false;
        })()
      `,
      returnByValue: true,
    }, { sessionId: session.sessionId });
    if (result.result.value) return true;
    await sleep(500);
  }
  return false;
}

async function clickStartPostButton(session: ChromeSession): Promise<void> {
  console.log('[linkedin] Looking for "Start a post" button...');

  // Wait a bit for page to fully load
  await sleep(3000);

  // Debug: Show all clickable elements
  const debugInfo = await session.cdp.send<{ result: { value: string } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const results = [];
        const all = document.querySelectorAll('*');
        for (const el of all) {
          if (el.offsetParent !== null) {
            const rect = el.getBoundingClientRect();
            const tag = el.tagName.toLowerCase();
            const classList = el.className || '';
            const text = (el.textContent || '').trim().substring(0, 30);
            const ariaLabel = el.getAttribute('aria-label') || '';

            // Look for buttons/divs/spans with relevant text
            if ((tag === 'button' || tag === 'div' || tag === 'span') &&
                rect.width > 50 && rect.width < 500 && rect.height > 30 && rect.height < 100) {
              const hasRelevantText = text.includes('post') || text.includes('Post') ||
                                       text.includes('分享') || text.includes('發佈') ||
                                       ariaLabel.includes('post') || ariaLabel.includes('Post') ||
                                       classList.includes('share');
              if (hasRelevantText) {
                results.push(tag + '@' + Math.round(rect.x) + ',' + Math.round(rect.y) +
                  '[' + Math.round(rect.width) + 'x' + Math.round(rect.height) + ']: ' +
                  classList.substring(0, 40) + ': ' + text + ' | aria: ' + ariaLabel);
              }
            }
          }
        }
        return results.slice(0, 20).join(' | ');
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId, timeoutMs: 30_000 });

  console.log(`[linkedin] Candidate elements: ${debugInfo.result.value?.substring(0, 500) || 'none'}`);

  // Try to find and click the button using multiple strategies
  const clicked = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
    expression: `
      (function() {
        // Strategy 1: Look for elements with aria-label containing "post" or "分享"
        const all = document.querySelectorAll('*');
        for (const el of all) {
          if (el.offsetParent !== null) {
            const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
            const text = (el.textContent || '').trim().toLowerCase();

            if ((ariaLabel.includes('post') || ariaLabel.includes('分享') || ariaLabel.includes('發佈')) ||
                (text === 'start a post' || text === 'start post' || text === 'start a post ')) {
              el.scrollIntoView({ block: 'center' });
              el.click();
              return true;
            }
          }
        }

        // Strategy 2: Look for specific class names
        const shareBox = document.querySelector('.share-box-feed-entry__trigger, [data-control-name="share_box"]');
        if (shareBox && shareBox.offsetParent !== null) {
          shareBox.scrollIntoView({ block: 'center' });
          shareBox.click();
          return true;
        }

        // Strategy 3: Look for buttons with "Create" or "Post" icon
        const buttons = document.querySelectorAll('button, div[role="button"]');
        for (const btn of buttons) {
          if (btn.offsetParent !== null) {
            const classList = btn.className || '';
            if (classList.includes('create') || classList.includes('share') || classList.includes('post')) {
              btn.scrollIntoView({ block: 'center' });
              btn.click();
              return true;
            }
          }
        }

        return false;
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId });

  if (!clicked.result.value) {
    // Try clicking at a specific position (LinkedIn usually has the button at top-left or center)
    console.log('[linkedin] Trying to click at common button position...');
    await session.cdp.send('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x: 200,
      y: 200,
      button: 'left',
      clickCount: 1
    }, { sessionId: session.sessionId });
    await sleep(50);
    await session.cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x: 200,
      y: 200,
      button: 'left',
      clickCount: 1
    }, { sessionId: session.sessionId });
  }

  console.log('[linkedin] Button clicked');
  await sleep(3000);
}

async function fillEditor(session: ChromeSession, text: string): Promise<void> {
  console.log('[linkedin] Waiting for editor to load...');
  await sleep(3000);

  // Debug: Show all editable elements
  const editorDebug = await session.cdp.send<{ result: { value: string } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const results = [];
        const all = document.querySelectorAll('*');
        for (const el of all) {
          if (el.offsetParent !== null) {
            const tag = el.tagName.toLowerCase();
            const classList = el.className || '';
            const contentEditable = el.getAttribute('contenteditable');
            const role = el.getAttribute('role');
            const placeholder = el.getAttribute('placeholder') || '';

            // Look for potential editor elements
            if (contentEditable === 'true' || role === 'textbox' || placeholder) {
              const rect = el.getBoundingClientRect();
              if (rect.width > 100 && rect.height > 30) {
                results.push(tag + '.' + classList.substring(0, 40) +
                  ': ce=' + contentEditable + ', role=' + role + ', ph=' + placeholder.substring(0, 30));
              }
            }
          }
        }
        return results.slice(0, 20).join(' | ');
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId, timeoutMs: 30_000 });

  console.log(`[linkedin] Editor candidates: ${editorDebug.result.value?.substring(0, 500) || 'none'}`);

  // Wait for editor with extended timeout
  let found = await waitForElement(session, EDITOR_SELECTORS, 15_000);

  // If not found, try to find any contenteditable element
  if (!found) {
    console.log('[linkedin] Standard selectors not found, trying contenteditable...');
    const hasContentEditable = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
      expression: `
        (function() {
          const editables = document.querySelectorAll('[contenteditable="true"], [role="textbox"], div[placeholder]');
          for (const el of editables) {
            if (el.offsetParent !== null) {
              const rect = el.getBoundingClientRect();
              if (rect.width > 100 && rect.height > 30) {
                el.focus();
                el.click();
                return true;
              }
            }
          }
          return false;
        })()
      `,
      returnByValue: true,
    }, { sessionId: session.sessionId });

    found = hasContentEditable.result.value;
  }

  if (!found) {
    console.log('[linkedin] Editor not found, trying to type anyway...');
  }

  // Type text using CDP input
  console.log('[linkedin] Typing content...');
  await session.cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        // Try to find and focus the editor
        const selectors = ${JSON.stringify(EDITOR_SELECTORS)};
        for (const selector of selectors) {
          const el = document.querySelector(selector);
          if (el && el.offsetParent !== null) {
            el.focus();
            el.click();
            return true;
          }
        }

        // Fallback: find any contenteditable
        const editables = document.querySelectorAll('[contenteditable="true"], [role="textbox"]');
        for (const el of editables) {
          if (el.offsetParent !== null) {
            el.focus();
            el.click();
            return true;
          }
        }

        // Last resort: click in the middle of the page
        document.body.focus();
        return false;
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId });

  await sleep(500);

  // Type the text
  await typeText(session, text);
  console.log('[linkedin] Content typed');
  await sleep(1000);
}

async function uploadImages(session: ChromeSession, images: string[]): Promise<void> {
  if (images.length === 0) return;

  console.log(`[linkedin] Uploading ${images.length} image(s)...`);

  for (const imagePath of images) {
    if (!fs.existsSync(imagePath)) {
      console.warn(`[linkedin] Image not found: ${imagePath}`);
      continue;
    }

    console.log(`[linkedin] Processing: ${imagePath}`);

    // Look for file input
    const fileInputFound = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
      expression: `
        (function() {
          const inputs = document.querySelectorAll('input[type="file"]');
          for (const input of inputs) {
            if (input.offsetParent !== null) {
              return true;
            }
          }
          return false;
        })()
      `,
      returnByValue: true,
    }, { sessionId: session.sessionId });

    if (!fileInputFound.result.value) {
      console.warn('[linkedin] File input not found. You may need to add images manually.');
      continue;
    }

    // Convert image to base64 and upload
    const imageBuffer = fs.readFileSync(imagePath);
    const base64Image = imageBuffer.toString('base64');
    const mimeType = path.extname(imagePath) === '.png' ? 'image/png' : 'image/jpeg';

    // Upload using file input
    await session.cdp.send('Runtime.evaluate', {
      expression: `
        (function() {
          const inputs = document.querySelectorAll('input[type="file"]');
          for (const input of inputs) {
            if (input.offsetParent !== null) {
              const file = new File([Uint8Array.from(atob('${base64Image}'), c => c.charCodeAt(0))], '${path.basename(imagePath)}', { type: '${mimeType}' });
              const dataTransfer = new DataTransfer();
              dataTransfer.items.add(file);
              input.files = dataTransfer.files;
              input.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
          }
          return false;
        })()
      `,
      returnByValue: true,
    }, { sessionId: session.sessionId });

    console.log('[linkedin] Waiting for upload to complete...');
    await sleep(3000);
  }

  console.log('[linkedin] Image upload complete');
}

async function submitPost(session: ChromeSession): Promise<void> {
  console.log('[linkedin] Looking for Post button...');

  // Wait a bit for UI to stabilize
  await sleep(3000);

  // Debug: Show all buttons
  const buttonDebug = await session.cdp.send<{ result: { value: string } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const results = [];
        const all = document.querySelectorAll('*');
        for (const el of all) {
          if (el.offsetParent !== null) {
            const tag = el.tagName.toLowerCase();
            const classList = el.className || '';
            const text = (el.textContent || '').trim().substring(0, 30);
            const ariaLabel = el.getAttribute('aria-label') || '';

            // Look for buttons in the bottom area of posting modal
            const rect = el.getBoundingClientRect();
            if ((tag === 'button' || tag === 'div' || tag === 'span') &&
                rect.width > 50 && rect.width < 300 && rect.height > 30 && rect.height < 80) {
              const hasPostText = text.includes('Post') || text.includes('post') ||
                                  text.includes('发布') || text.includes('發佈') ||
                                  text.includes('Send') || text.includes('send') ||
                                  ariaLabel.includes('Post') || ariaLabel.includes('post') ||
                                  classList.includes('post') || classList.includes('share') ||
                                  classList.includes('submit') || classList.includes('primary');
              if (hasPostText) {
                results.push(tag + '@' + Math.round(rect.x) + ',' + Math.round(rect.y) +
                  ': ' + classList.substring(0, 40) + ': ' + text);
              }
            }
          }
        }
        return results.slice(0, 15).join(' | ');
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId, timeoutMs: 30_000 });

  console.log(`[linkedin] Post button candidates: ${buttonDebug.result.value?.substring(0, 500) || 'none'}`);

  // Try to find and click the post button using multiple strategies
  const clicked = await session.cdp.send<{ result: { value: boolean } }>('Runtime.evaluate', {
    expression: `
      (function() {
        // Strategy 1: Use predefined selectors
        const selectors = ${JSON.stringify(POST_BUTTON_SELECTORS)};
        for (const selector of selectors) {
          const el = document.querySelector(selector);
          if (el && el.offsetParent !== null && !el.disabled) {
            el.scrollIntoView({ block: 'center' });
            el.click();
            return true;
          }
        }

        // Strategy 2: Look for buttons with "Post" text
        const allButtons = document.querySelectorAll('button, div[role="button"]');
        for (const btn of allButtons) {
          if (btn.offsetParent !== null && !btn.disabled) {
            const text = (btn.textContent || '').trim();
            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
            const classList = (btn.className || '').toLowerCase();

            if (text === 'Post' || text === 'post' || text === '发布' || text === '發佈' ||
                ariaLabel.includes('post') || ariaLabel.includes('publish') ||
                classList.includes('post') || classList.includes('share-primary') ||
                classList.includes('submit')) {
              btn.scrollIntoView({ block: 'center' });
              btn.click();
              return true;
            }
          }
        }

        // Strategy 3: Look for primary action buttons in modal footer
        const modalButtons = document.querySelectorAll('.share-actions__primary-action, .artdeco-button--primary, button[data-control-name="share.post"]');
        for (const btn of modalButtons) {
          if (btn.offsetParent !== null && !btn.disabled) {
            btn.scrollIntoView({ block: 'center' });
            btn.click();
            return true;
          }
        }

        return false;
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId });

  if (clicked.result.value) {
    console.log('[linkedin] Post submitted!');
    await sleep(3000);
  } else {
    // Try pressing Enter as fallback
    console.log('[linkedin] Button not found, trying Enter key...');
    await session.cdp.send('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13
    }, { sessionId: session.sessionId });
    await session.cdp.send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13
    }, { sessionId: session.sessionId });
    await sleep(2000);

    // If still not submitted, throw error
    console.log('[linkedin] If post not submitted, please click manually. Browser will stay open for 10s...');
    await sleep(10000);
  }
}

export async function postToLinkedIn(options: PostOptions): Promise<void> {
  const { text = '', images = [], submit = false, profileDir } = options;

  if (!text && images.length === 0) {
    throw new Error('Provide text or at least one image.');
  }

  console.log(`[linkedin] Content length: ${text.length} chars`);
  console.log(`[linkedin] Images: ${images.length}`);

  const { cdp, chrome } = await launchChrome(LINKEDIN_FEED_URL, profileDir);

  try {
    console.log('[linkedin] Waiting for page load...');
    await sleep(8000);

    let session = await getPageSession(cdp, LINKEDIN_DOMAIN);

    // Wait for actual page to load
    console.log('[linkedin] Waiting for page content to load...');
    let url = await evaluate<string>(session, 'window.location.href');
    let retries = 0;
    while ((url === 'about:blank' || !url.includes(LINKEDIN_DOMAIN)) && retries < 20) {
      await sleep(1000);
      url = await evaluate<string>(session, 'window.location.href');
      retries++;
      if (retries % 3 === 0) {
        console.log(`[linkedin] Still loading... (${url})`);
      }
    }

    console.log(`[linkedin] Current URL: ${url}`);

    // Wait for login if needed
    if (url.includes('login') || url.includes('auth') || url.includes('checkpoint')) {
      console.log('[linkedin] Please log in to LinkedIn...');
      console.log('[linkedin] Waiting for login (up to 5 minutes)...');

      const start = Date.now();
      while (Date.now() - start < 300_000) {
        await sleep(3000);
        const currentUrl = await evaluate<string>(session, 'window.location.href');
        if (currentUrl.includes('feed') && !currentUrl.includes('login')) {
          console.log('[linkedin] Logged in!');
          await sleep(2000);
          session = await getPageSession(cdp, LINKEDIN_DOMAIN);
          break;
        }
        const elapsed = Math.floor((Date.now() - start) / 1000);
        if (elapsed % 15 === 0) {
          console.log(`[linkedin] Still waiting... (${elapsed}s)`);
        }
      }
    }

    // Wait for feed to load
    await sleep(3000);

    // Click "Start a post" button
    await clickStartPostButton(session);

    // Fill content
    if (text) {
      await fillEditor(session, text);
    }

    // Upload images
    if (images.length > 0) {
      await uploadImages(session, images);
    }

    // Submit or preview
    if (submit) {
      await submitPost(session);
    } else {
      console.log('[linkedin] Preview mode - Post ready to review');
      console.log('[linkedin] Browser will stay open for 30 seconds...');
      await sleep(30_000);
    }

  } finally {
    console.log('[linkedin] Closing browser...');
    cdp.close();
    try {
      chrome.kill('SIGTERM');
      await sleep(2000);
      if (!chrome.killed) {
        chrome.kill('SIGKILL');
      }
    } catch {}
  }
}

function printUsage(): never {
  console.log(`Post to LinkedIn using Chrome CDP automation

Usage:
  npx -y bun linkedin-browser.ts [options] [text]

Options:
  --image <path>   Add image (can be repeated)
  --submit         Actually post (default: preview only)
  --profile <dir>  Chrome profile directory
  --help           Show this help

Examples:
  npx -y bun linkedin-browser.ts "Hello LinkedIn!"
  npx -y bun linkedin-browser.ts "Check this out" --image ./photo.jpg --submit
`);
  process.exit(0);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) printUsage();

  const images: string[] = [];
  let submit = false;
  let profileDir: string | undefined;
  const textParts: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    if (arg === '--image' && args[i + 1]) {
      images.push(args[++i]!);
    } else if (arg === '--submit') {
      submit = true;
    } else if (arg === '--profile' && args[i + 1]) {
      profileDir = args[++i];
    } else if (!arg.startsWith('-')) {
      textParts.push(arg);
    }
  }

  const text = textParts.join(' ').trim() || '';

  if (!text && images.length === 0) {
    console.error('Error: Provide text or at least one image.');
    process.exit(1);
  }

  await postToLinkedIn({ text, images, submit, profileDir });
}

await main().catch((err) => {
  console.error(`Error: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
