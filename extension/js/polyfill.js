/**
 * Browser API Polyfill - Provides cross-browser compatibility
 *
 * Firefox uses browser.* with Promises
 * Chrome uses chrome.* with callbacks (but also supports chrome.* as alias)
 *
 * This polyfill ensures consistent Promise-based API across browsers
 */

// Create browser namespace if it doesn't exist (Chrome)
if (typeof browser === 'undefined') {
    window.browser = {
        tabs: {
            query: (queryInfo) => {
                return new Promise((resolve) => {
                    chrome.tabs.query(queryInfo, resolve);
                });
            }
        },
        storage: {
            local: {
                get: (keys) => {
                    return new Promise((resolve) => {
                        chrome.storage.local.get(keys, resolve);
                    });
                },
                set: (items) => {
                    return new Promise((resolve) => {
                        chrome.storage.local.set(items, resolve);
                    });
                }
            }
        },
        cookies: {
            getAll: (details) => {
                return new Promise((resolve) => {
                    chrome.cookies.getAll(details, resolve);
                });
            }
        }
    };
}

export default browser;
