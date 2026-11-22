// start with npm run api

import { createServer } from 'node:http'
import { HttpError, readJsonBody, sendJson } from './http.js'
import { connectAs } from './supabase.js'
import { findRoute } from './routes.js'

const PORT = Number(process.env.API_PORT) || 3001

// createServer runs this function once for every request that comes in
const server = createServer(async (request, response) => {
    
    // allowed because the frontend sends them
    response.setHeader('Access-Control-Allow-Origin', '*')
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Guest-Job-Token')

    //browsers send an OPTIONS "may I" request before the real request, accept
    if (request.method === 'OPTIONS') return sendJson(response, 204)

    const url = new URL(request.url, `http://localhost:${PORT}`)
    let status = 500

    try {
        // figures out what route this is
        const route = findRoute(request.method, url.pathname)
        if (!route) throw new HttpError(404, `No endpoint for ${request.method} ${url.pathname}`)
        
        // read json body and connect to supabase as whoever sent this
        const body = await readJsonBody(request)
        const { db, user } = await connectAs(request)

        // run the route it returns {status, body}
        const result = await route.handler({
            params: route.params,
            query: Object.fromEntries(url.searchParams),
            body,
            db,
            user,
        })
        status = result.status
        sendJson(response, result.status, result.body)
    } catch (error) {
        // show httperrors messages
        status = error instanceof HttpError ? error.status : 500
        if (status === 500) console.error(error)
        sendJson(response, status, {
            error: status === 500 ? 'Something went wrong on the server' : error.message,
        })
    }

    console.log(`${request.method} ${url.pathname} -> ${status}`)
})

server.listen(PORT, () => {
    console.log(`API running at http://localhost:${PORT}`)
})