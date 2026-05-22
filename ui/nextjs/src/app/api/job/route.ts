import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL!;
const API_USERNAME = process.env.API_USERNAME!;
const API_PASSWORD = process.env.API_PASSWORD!;

function basicAuth() {
  return 'Basic ' + Buffer.from(`${API_USERNAME}:${API_PASSWORD}`).toString('base64');
}

export async function POST(req: NextRequest) {
  const body = await req.json();

  const res = await fetch(BACKEND_URL.replace(/\/$/, '') + '/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: basicAuth(),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    return NextResponse.json({ error: await res.text() }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}

export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get('id');
  if (!jobId) return NextResponse.json({ error: 'Missing id' }, { status: 400 });

  const res = await fetch(`${BACKEND_URL.replace(/\/$/, '')}/${jobId}`, {
    headers: { Authorization: basicAuth() },
  });

  if (!res.ok) {
    return NextResponse.json({ error: await res.text() }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
