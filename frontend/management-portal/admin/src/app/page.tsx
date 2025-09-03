import { redirect } from 'next/navigation';

export default function HomePage() {
  // Redirect to dashboard for authenticated users, login for unauthenticated
  redirect('/dashboard');
}
