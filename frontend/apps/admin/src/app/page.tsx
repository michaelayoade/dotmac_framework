import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { LoginForm } from '../components/auth/LoginForm';
import { AdminDashboard } from '../components/dashboard/AdminDashboard';

async function getUser() {
  const cookieStore = cookies();
  const authToken = cookieStore.get('auth-token');
  const userData = cookieStore.get('user-data');
  
  if (!authToken || !userData) {
    return null;
  }
  
  try {
    return JSON.parse(userData.value);
  } catch {
    return null;
  }
}

export default async function AdminHomePage() {
  const user = await getUser();

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900">DotMac Admin Portal</h1>
            <p className="mt-2 text-gray-600">Sign in to manage your ISP infrastructure</p>
          </div>
          <LoginForm />
        </div>
      </div>
    );
  }

  // User is authenticated, redirect to dashboard
  redirect('/dashboard');
}