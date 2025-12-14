import { NestFactory } from '@nestjs/core';
import { ValidationPipe, RequestMethod } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Prefijo global para todas las rutas HTTP
  app.setGlobalPrefix('api', {
    exclude: [
      { path: 'v1/report', method: RequestMethod.ALL },
      { path: 'v1/report/(.*)', method: RequestMethod.ALL },
    ],
  });

  // Configurar CORS
  const port = process.env.PORT || 3001;
  app.enableCors({
    origin: ['http://localhost:3000', 'http://localhost:3001'],
    credentials: true,
  });

  // Configurar validación global
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  // Configurar Swagger
  const config = new DocumentBuilder()
    .setTitle('VX Control Center API')
    .setDescription('Sistema de registro y monitoreo de equipos')
    .setVersion('1.0')
    .addTag('reports', 'Reportes de verificación (v1)')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document, { useGlobalPrefix: true });

  // Iniciar servidor
  await app.listen(port, '0.0.0.0');
  console.log(`🚀 API corriendo en http://localhost:${port}`);
  console.log(`📚 Docs disponibles en http://localhost:${port}/api/docs`);
}

bootstrap();
