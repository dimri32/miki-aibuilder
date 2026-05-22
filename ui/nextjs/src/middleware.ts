import { NextRequest, NextResponse } from 'next/server';

export function middleware(req: NextRequest) {
  const auth = req.cookies.get('auth');
  const { pathname } = req.nextUrl;

  if (pathname.startsWith('/dashboard') && auth?.value !== 'true') {
    return NextResponse.redirect(new URL('/', req.url));
  }
  if (pathname === '/' && auth?.value === 'true') {
    return NextResponse.redirect(new URL('/dashboard', req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/', '/dashboard', '/dashboard/:path*'],
};
