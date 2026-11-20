// helpers that server.js and routes.js both use

// error that remembers which http status code to send back
export class HttpError extends Error {
    constructor(status, message) {
        super(message)
        this.status = status
    }
}

// request body arrives in chunks so this turns the JSON text into a JS object
export async function readJsonBody(request) {
    let text = ''
    for await (const chunk of request) text += chunk
    if (!text) return {}
    try {
        return JSON.parse(text)
    } catch {
        throw new HttpError(400, 'Request body must be valid JSON')
    }
}

// sends response 
export function sendJson(response, status, body) {
    if (body === undefined) {
        response.writeHead(status).end()
    } else {
        response.writeHead(status, { 'Content-Type': 'application/json'}).end(JSON.stringify(body))
    }
}

// checks real path like /api/sounds/abc against pattern like /api/sounds/:id
export function matchPath(pattern, path) {
  const patternParts = pattern.split('/')
  const pathParts = path.replace(/\/$/, '').split('/')
  if (patternParts.length !== pathParts.length) return null

  const params = {}
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i])
    } else if (patternParts[i] !== pathParts[i]) {
      return null
    }
  }
  return params
}