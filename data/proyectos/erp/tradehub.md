**Proyecto: tradehub**

### Tecnologías

- **Plataforma de Desarrollo:** AppSheet (Google Cloud).
    
- **Base de Datos:** Google Sheets (Estructura relacional).
    
- **Almacenamiento de Archivos:** Google Drive.
    
- **Automatización:** AppSheet Automation (Bots).
    
- **Lenguajes/Sintaxis:** AppSheet Expressions.
    
- **Metodologías de Diseño:** BPMN 2.0, UML, DBML, 3FN (Tercera Forma Normal).
    
- **Infraestructura:** SaaS / Serverless (Google Cloud).
    

### Tipo

Sistema ERP (Enterprise Resource Planning) y CRM (Customer Relationship Management) verticalizado para comercio electrónico y logística inversa, desarrollado bajo arquitectura Low-Code.

### Problema que resuelve

Gestión fragmentada y manual del ciclo de vida de hardware electrónico usado (dispositivos Kindle) con operación logística internacional (EE. UU. - Colombia). Aborda la falta de trazabilidad unitaria por número de serie, la desconexión entre la compra de lotes y la venta individual, y la ausencia de control en los costos de reparación y logística de importación.

### Arquitectura / Implementación técnica

**Rol del desarrollador** Responsable del ciclo completo de ingeniería de la solución:

- **Diseño de modelo relacional:** Estructuración y normalización de la base de datos (3FN).
    
- **Modelado BPMN:** Definición de flujos de trabajo y procesos de negocio.
    
- **Implementación AppSheet:** Desarrollo de la lógica de aplicación, UX/UI y expresiones de datos.
    
- **Configuración de bots:** Orquestación de automatizaciones y disparadores de eventos.
    
- **Definición de seguridad:** Configuración de filtros de seguridad (RLS) y control de acceso (RBAC).
    

**Backend** La lógica de negocio reside en la infraestructura serverless de AppSheet. Se utilizan **AppSheet Expressions** para definir columnas virtuales, validaciones de datos y lógica condicional. El sistema implementa "Soft Delete" mediante columnas booleanas (`isActive`) para preservar el historial de datos sin eliminación física.

**Frontend** Interfaz móvil nativa (Android/iOS) y web generada dinámicamente por AppSheet. La visualización de datos se gestiona mediante **Slices** (vistas filtradas), que segregan la información presentada en función del rol del usuario y el estado de los datos.

**Base de datos** Persistencia de datos en **Google Sheets**, modelada estrictamente como una base de datos relacional en **Tercera Forma Normal (3FN)**.

- **Esquema:** Consta de aproximadamente 35 tablas vinculadas y más de 378 columnas.
    
- **Tablas Core:** `productos` (catálogo), `inventario` (instancias serializadas), `orden_venta` (cabecera transaccional), `orden_detalle` (líneas de transacción), `movimientos_inventario` (auditoría).
    

**Infraestructura** Totalmente alojada en Google Cloud. No requiere servidores dedicados. La escalabilidad depende de las cuotas de la plataforma AppSheet y las limitaciones de celdas de Google Sheets.

**Integraciones**

- **Google Drive:** Almacenamiento de objetos binarios (imágenes de evidencia de reparación, comprobantes de pago, guías de envío) vinculados mediante URLs relativas en la base de datos.
    
- **Correos Electrónicos:** Disparadores automáticos para notificaciones de estado.
    

**Flujo de datos**

1. **Adquisición:** Registro de lotes en `compras_lote` con integración de links de rastreo internacional.
    
2. **Serialización:** Desagregación del lote en ítems individuales en la tabla `inventario` con estado inicial "En Inspección".
    
3. **Procesamiento Técnico:** Transición de estados mediante evaluaciones (`En Reparación` -> `Disponible` o `Baja Técnica`).
    
4. **Comercialización:** Bloqueo de registros en `inventario` al asociarse a una `orden_venta`.
    
5. **Cierre:** Cambio de estado a "Vendido" ejecutado por Bots tras la confirmación de pago y despacho.
    

### Funcionalidades clave

- **Trazabilidad Unitaria (End-to-End):** Seguimiento por número de serie desde la compra del lote en origen hasta la entrega al cliente final.
    
- **Máquina de Estados de Inventario:** Control estricto de transiciones (Disponible 🟢, Vendido 🔴, En Reparación 🔧, Baja Técnica ⚫) para asegurar la integridad del stock.
    
- **Seguridad a Nivel de Fila (RLS):** Filtros de seguridad (Security Filters) que restringen el acceso a los datos (Lectura/Escritura) basándose en el email del usuario y su rol asignado (ADMIN, TECNICO, VENTAS, LOGISTICA).
    
- **Gestión de Logística Internacional:** Módulos para consolidación de envíos en Miami (`consolidacion_envios`) y seguimiento de courier local (`control_envios`).
    
- **Diagnóstico y Reparación:** Registro detallado de intervenciones técnicas y costos asociados por unidad.
    

### Resultados / Impacto

- Centralización de operaciones de compra, logística, técnica y ventas en una única fuente de verdad.
    
- Eliminación de redundancia de datos mediante la normalización 3FN.
    
- Automatización del cambio de estados de inventario, reduciendo errores humanos en la disponibilidad de productos.
    
- Control financiero granular sobre la rentabilidad por lote y por unidad reparada.