-- CreateTable
CREATE TABLE "reports" (
    "id" TEXT NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL,
    "migrasfreeCid" TEXT NOT NULL,
    "usuarioGrafico" TEXT NOT NULL,
    "verificacionEquipos" JSONB NOT NULL,
    "resumen" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "reports_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "reports_timestamp_idx" ON "reports"("timestamp");

-- CreateIndex
CREATE INDEX "reports_migrasfreeCid_idx" ON "reports"("migrasfreeCid");
