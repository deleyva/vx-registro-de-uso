import { PrismaClient } from '@prisma/client';

// Singleton de Prisma Client
const globalForPrisma = global as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

// Exportar tipos y clases de Prisma
export { PrismaClient } from '@prisma/client';
export * from '@prisma/client';
