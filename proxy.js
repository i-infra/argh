/**
 * An object with different URLs to fetch
 * @param {Object} ORIGINS
 */

const ORIGINS = {
  "api.tweeter.workers.dev": "api.twitter.com",
  "root.tweeter.workers.dev": "twitter.com"
}

async function handleRequest(request) {
  const url = new URL(request.url)
  // Check if incoming hostname is a key in the ORIGINS object
  if (url.hostname in ORIGINS) {
    const target = ORIGINS[url.hostname]
    url.hostname = target
    // If it is, proxy request to that third party origin
    return await fetch(url.toString(), request)
  }

  // Otherwise, process request as normal
  return await fetch(request)
}

addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request))
})
