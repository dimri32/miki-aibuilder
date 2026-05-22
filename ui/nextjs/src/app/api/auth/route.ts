import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const { username, password } = await req.json();

  if (
    username === process.env.API_USERNAME &&
    password === process.env.API_PASSWORD
  ) {
    const res = NextResponse.json({ ok: true });
    res.cookies.set('auth', 'true', {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 8,
    });
    return res;
  }
  return NextResponse.json({ ok: false }, { status: 401 });
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set('auth', '', { httpOnly: true, sameSite: 'lax', path: '/', maxAge: 0 });
  return res;
}
