## proyecto: TradeHUB, tecnologias: [AppSheet, Google Sheets, Google Drive,Low-Code] rol_rag: Especificación Técnica de Sistema ERP/CRM

# Documentación Técnica: TradeHUB

## 1. Visión General

**TradeHUB** es un sistema integral de gestión de recursos empresariales (ERP) y relaciones con clientes (CRM) desarrollado bajo una arquitectura _Low-Code_ para **Kindle Cafe Shop CO**.

El sistema resuelve la problemática de la gestión de inventario de hardware usado (específicamente dispositivos Kindle) con operación logística internacional (EE. UU. → Colombia). Su función principal es garantizar la trazabilidad unitaria de cada dispositivo mediante número de serie, desde la compra en lotes en el extranjero, pasando por diagnóstico técnico, hasta la venta y entrega final. Reemplaza procesos manuales (Excel/WhatsApp) por una aplicación móvil nativa centralizada.

## 2. Arquitectura y Componentes

El sistema opera sobre una infraestructura _Serverless_ gestionada por Google Cloud a través de AppSheet.

### Componentes Lógicos:

- **Frontend (App):** Aplicación móvil (Android/iOS) generada por AppSheet, que sirve como interfaz de captura y consulta. Utiliza "Slices" (vistas filtradas de datos) para segregar funciones según el rol del usuario.
    
- **Backend (Data Layer):**Google Sheets actúa como el motor de base de datos relacional. Aunque es una hoja de cálculo, los datos están estructurados en **3FN (Tercera Forma Normal)** para evitar redundancia.
    
- **Almacenamiento de Evidencias:** Google Drive se utiliza para almacenar imágenes de reparaciones, comprobantes de pago y evidencias de envíos, vinculadas a los registros mediante URLs relativas.
    
- **Motor de Automatización:** "AppSheet Automation" (Bots) ejecuta tareas en segundo plano, como cambios de estado de inventario al confirmarse una venta o notificaciones de logística.
    

## 3. Especificaciones Técnicas (Stack)

- **Plataforma de Desarrollo:** AppSheet (Google Cloud).
    
- **Base de Datos:** Google Sheets (Relacional, ~35 tablas vinculadas).
    
- **Lenguaje de Expresiones:** AppSheet Expressions (fórmulas lógicas nativas de la plataforma para columnas virtuales y validaciones).
    
- **Infraestructura:** SaaS (Software as a Service), sin servidores dedicados.
    
- **Volumen de Datos:** +35 tablas, +378 columnas, gestionando inventarios de alta rotación.
    

## 4. Flujo de Datos y Lógica de Negocio

### 4.1 Ciclo de Vida del Producto (End-to-End)

1. **Ingesta (Compras):** Se registra un lote (`compras_lote`) proveniente de EE. UU.
    
2. **Serialización (Inventario):** Cada ítem físico se ingresa en la tabla `inventario` con su **Número de Serie** único. Estado inicial: `En Inspección`.
    
3. **Diagnóstico:** El rol Técnico evalúa el dispositivo.
    
    - _Si falla:_ Pasa a tabla `reparaciones`. Estado: `En Reparación`.
        
    - _Si aprueba:_ Estado cambia a `Disponible`.
        
4. **Transacción (Venta):**
    
    - El vendedor crea una `orden_venta`.
        
    - Selecciona ítems `Disponibles` en `orden_detalle`.
        
    - El sistema bloquea esos ítems para otros vendedores.
        
5. **Salida (Logística):** Al confirmar pago, el Bot cambia el estado del ítem a `Vendido` y se genera el registro en `envio_venta`.
    

### 4.2 Máquina de Estados (Semáforos)

El sistema valida estrictamente las transiciones de estado para evitar errores contables:

- **Estados de Inventario:**
    
    - `Disponible` 🟢 (Visible para vendedores).
        
    - `Vendido` 🔴 (Bloqueado, propiedad del cliente).
        
    - `En Reparación` 🔧 (Visible solo para técnicos).
        
    - `Baja Técnica` ⚫ (Retirado del inventario activo).
        
- **Estados de Orden de Venta:**
    
    - `Creado` → `Aprobado` → `Enviado` → `Entregado`.
        

## 5. Esquema de Datos y Configuración

A diferencia de un entorno tradicional con `.env`, TradeHUB se configura mediante la estructura de sus tablas y permisos de seguridad.

### Tablas Principales (Schema)

- **`productos`:** Catálogo maestro (SKUs, Modelos).
    
- **`inventario`:** Tabla transaccional central. PK: `ID_Inventario` (Serial). FK: `ID_Producto`.
    
- **`orden_venta`:** Cabecera de factura. Campos: `Cliente`, `Fecha`, `Estado_Pago`, `Total_Neto`.
    
- **`orden_detalle`:** Líneas de factura. Vincula `orden_venta` con `inventario`.
    

### Roles y Permisos (Security Filters)

El sistema filtra los datos (Row-Level Security) según el email del usuario logueado:

Plaintext

```
ROLE_ADMIN: Acceso total (CRUD) a todas las tablas y vistas financieras.
ROLE_TECNICO: Read/Edit en 'inventario' (solo estado) y 'reparaciones'.
ROLE_VENTAS: Read 'inventario' (solo disponibles), Create 'orden_venta'.
ROLE_LOGISTICA: Read 'orden_venta' (solo aprobadas), Edit 'envio_venta'.
```

## 6. Glosario para Modelos de Lenguaje (LLM context)

- **Slice:** En el contexto de AppSheet, es un subconjunto virtual de una tabla (ej. "Ventas de Hoy"). No es una tabla física nueva, es una vista filtrada.
    
- **Batch Tracking:** Capacidad del sistema de rastrear un grupo de dispositivos hasta su factura de compra original (`compras_lote`) para calcular márgenes de ganancia reales.
    
- **Soft Delete:** Los registros no se borran físicamente. Se usa una columna `isActive` (TRUE/FALSE). Si un usuario pregunta "¿Borraste la venta?", la respuesta técnica es "Se marcó como inactiva para mantener integridad referencial".
    
- **Trazabilidad Unitaria:** A diferencia del retail masivo que cuenta "5 manzanas", TradeHUB cuenta "La manzana con ID #123". Cada fila de inventario es un objeto físico único.
    


## 7. Infraestructura y Despliegue
Este proyecto es **100% Serverless** y está alojado en la nube de Google.
**NOTA IMPORTANTE:** A diferencia de otros proyectos del portafolio, TradeHUB **NO utiliza Docker**, ni servidores Linux, ni contenedores. Depende exclusivamente de la infraestructura PaaS de AppSheet.
---
