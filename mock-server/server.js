// Mock backend for local development. Start it with: npm run mock-api
// Data lives in memory, so changes reset every time the server restarts.
import { createServer } from 'node:http'
import { createMockApi } from './routes.js'

const PORT = Number(process.env.MOCK_API_PORT) || 3001
const handle = createMockApi()

// Reads the request body and parses it as JSON (empty body = {})
async function readBody(request) {
  let text = ''
  for await (const chunk of request) text += chunk
  return text ? JSON.parse(text) : {}
}

function send(response, status, body) {
  if (body === undefined) {
    response.writeHead(status).end()
  } else {
    response.writeHead(status, { 'Content-Type': 'application/json' }).end(JSON.stringify(body))
  }
}

const server = createServer(async (request, response) => {
  // Let other apps (other ports, the Python worker, etc.) call the mock API too
  response.setHeader('Access-Control-Allow-Origin', '*')
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  if (request.method === 'OPTIONS') return send(response, 204)

  let body
  try {
    body = await readBody(request)
  } catch {
    return send(response, 400, { error: 'Request body must be valid JSON' })
  }

  const url = new URL(request.url, `http://localhost:${PORT}`)
  const result = handle({
    method: request.method,
    path: url.pathname,
    query: Object.fromEntries(url.searchParams),
    body,
  })

  console.log(`${request.method} ${url.pathname} -> ${result.status}`)
  send(response, result.status, result.body)
})

server.listen(PORT, () => {
  console.log(`Mock API running at http://localhost:${PORT}`)
})
