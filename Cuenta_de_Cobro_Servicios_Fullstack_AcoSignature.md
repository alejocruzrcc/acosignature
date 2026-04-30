# CUENTA DE COBRO

**INGENIERÍA DISEÑO Y CONSTRUCCIÓN SAS**
**NIT 800163131-8**

---

## 1. Datos generales

- **Fecha de emisión:** 28/04/2026
- **Ciudad:** Cali
- **Cuenta de cobro No.:** CC-2026-001

### Debe a:

- **Nombre:** Luis Alejandro Cruz Ordóñez
- **Documento:** C.C. 1061769227

### Datos de pago

- **Forma de pago:** Contado (pago único contra entrega)
- **Medio de pago:** Transferencia bancaria
- **Banco:** Bancolombia
- **Tipo de cuenta:** Ahorros
- **Número de cuenta:** 83899513897

---

## 2. Concepto

Cobro por **servicios profesionales de desarrollo de software fullstack** correspondientes al diseño, construcción, puesta en marcha y entrega funcional de la plataforma **AcoSignature**, incluyendo backend, frontend, lógica de negocio, seguridad, flujo de firma digital secuencial, notificaciones, despliegue y estabilización inicial.

---

## 3. Alcance funcional entregado (detalle completo)

### 3.1 Gestión de usuarios y acceso

- Autenticación de usuarios con flujo de inicio y cierre de sesión.
- Manejo de perfiles con actualización de datos personales y firma guardada.
- Cambio de contraseña desde el portal.
- Control de acceso por roles y por relación con documentos (creador/firmante).

### 3.2 Gestión documental

- Creación de documentos PDF con metadatos (título, descripción y archivo).
- Asignación de firmantes por documento.
- Validación de formatos de archivo en carga de documentos.
- Visualización de detalle por documento con trazabilidad de estados.
- Descarga de documento firmado cuando aplica.

### 3.3 Flujo de firma digital

- Flujo de firma en 3 pasos (revisión, captura de firma, confirmación).
- Firma por dibujo (canvas), firma guardada o carga de imagen.
- Validación de formatos de imagen para firma (JPG, JPEG, PNG, WEBP, GIF y BMP).
- Registro de fecha, usuario e IP asociada al evento de firma.
- Bloqueo de firma cuando no corresponde al turno.

### 3.4 Flujo secuencial de firmantes

- Definición de orden de firma por documento.
- Constructor de firmantes con lista ordenable (drag and drop).
- Lógica de turnos para permitir firma y rechazo solo al firmante activo.
- Indicación en bandeja de quién está pendiente por firmar.

### 3.5 Rechazos y estados

- Rechazo por firmante con motivo obligatorio.
- Cambio a estado rechazado general cuando corresponde.
- Visualización de quién rechazó y motivo en interfaces de seguimiento.
- Estados gestionados: pendiente, firmado, aprobado, rechazado y archivado.

### 3.6 Bandejas y experiencia de usuario

- Bandeja principal de aprobaciones.
- Listados convertidos a tarjetas responsive para dispositivos móviles.
- Sección de documentos archivados separada del listado principal.
- Paginación progresiva en archivados (15 inicial + incrementos de 10).
- Acciones por tarjeta: ver, aprobar, rechazar, descargar, archivar y eliminar (según reglas).
- Confirmación modal para operaciones críticas (eliminación).

### 3.7 Reglas de negocio implementadas

- Impedir firma o rechazo cuando no es turno del firmante.
- Permitir archivar documentos cerrados (aprobados/rechazados/firmados).
- Excluir archivados del listado principal.
- Eliminar documento solo cuando no esté completamente firmado por todos los firmantes.
- Redirección a login desde enlaces de correo cuando no hay sesión iniciada.

### 3.8 Notificaciones por correo

- Envío de correo al asignar firmantes.
- Plantillas HTML y texto plano mejoradas.
- Inclusión de identidad visual (logo institucional) en correo HTML.
- Enlaces directos al documento para gestión inmediata.
- Manejo robusto de errores de correo para no afectar transacciones de negocio.

### 3.9 Generación de PDF firmado

- Reconstrucción de PDF final anexando hoja de firmas.
- Inclusiones por firmante: nombre, cargo, documento y fecha de firma.
- Evidencia gráfica de firma en documento consolidado.

---

## 4. Especificaciones técnicas

### 4.1 Arquitectura y stack

- **Backend:** Python + Django + Django REST Framework.
- **Autenticación API:** JWT (SimpleJWT).
- **Base de datos:** PostgreSQL (compatible con Neon/Render).
- **Frontend portal:** Django Templates + CSS + JavaScript.
- **Servidor de estáticos:** WhiteNoise.
- **Despliegue:** Render (entorno productivo).

### 4.2 Seguridad y calidad

- Validaciones de entrada en backend y formularios.
- Control de permisos por rol y pertenencia documental.
- Protecciones de seguridad HTTP (headers y políticas configuradas).
- Trazabilidad de eventos de flujo documental.
- Manejo transaccional en operaciones críticas.

### 4.3 Integración y configuración

- Variables de entorno para configuración por ambiente.
- Configuración de correo SMTP para notificaciones.
- Endpoints API para integración externa.
- Compatibilidad responsive (desktop/tablet/móvil).

---

## 5. Resumen de trabajo profesional ejecutado

Se realizó la implementación integral de una solución fullstack para gestión y firma documental, cubriendo análisis funcional, modelado de datos, desarrollo backend, desarrollo frontend, pruebas funcionales, mejoras de experiencia de usuario, reglas de negocio avanzadas, notificaciones, despliegue y ajustes de estabilización en producción.

El producto fue entregado **funcional y operativo**, cumpliendo los requerimientos solicitados para su uso real en entorno productivo.

---

## 6. Valor total a pagar

**VALOR TOTAL SERVICIOS PROFESIONALES: $ 3.200.000 COP**
**(Tres millones doscientos mil pesos colombianos M/CTE)**

---

## 7. Condición de pago

- **Modalidad:** Pago de contado (un solo pago).
- **Estado de entrega:** Producto entregado y finalizado.

---

Atentamente,

**Luis Alejandro Cruz Ordóñez**
**C.C. 1061769227**
Dirección: Cra 119 # 60 - 144
Teléfono: 3116494967
