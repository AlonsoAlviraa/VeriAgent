import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { cookies } from "next/headers";

// Extend the built-in session and JWT types
declare module "next-auth" {
    interface Session {
        user: {
            is2FAVerified: boolean;
        } & DefaultSession["user"];
    }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        Credentials({
            name: "Credentials",
            credentials: {
                email: { label: "Email", type: "email" },
                password: { label: "Password", type: "password" },
            },
            async authorize(credentials) {
                // Mockup user for testing
                if (credentials?.email === "alonsotest@veriagent.com") {
                    return { id: "1", name: "Alonso Test", email: credentials.email as string };
                }
                return null;
            },
        }),
    ],
    session: { strategy: "jwt" },
    pages: {
        signIn: "/auth/login",
        verifyRequest: "/auth/verify-request",
        error: "/auth/error",
    },
    callbacks: {
        async jwt({ token, user, trigger, session }) {
            if (user) {
                // Initial login
                const cookieStore = await cookies();
                const trustedToken = cookieStore.get("device_trust_token")?.value;
                token.is2FAVerified = !!trustedToken;
            }

            if (trigger === "update" && session?.is2FAVerified !== undefined) {
                token.is2FAVerified = session.is2FAVerified;
            }

            return token;
        },
        async session({ session, token }) {
            if (token.sub && session.user) {
                session.user.id = token.sub;
                session.user.is2FAVerified = !!token.is2FAVerified;
            }
            return session;
        },
    },
},
    secret: process.env.AUTH_SECRET,
});
