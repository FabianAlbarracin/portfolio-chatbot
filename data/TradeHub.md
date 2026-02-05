# TradeHUB  
## Sistema interno de gestión de inventario, compras, ventas y logística de Kindles usados

---

## 1. Qué es este proyecto

TradeHUB es un **sistema interno tipo mini-ERP**, diseñado para gestionar de forma centralizada el ciclo completo de dispositivos Kindle usados: desde su adquisición en el exterior, revisión técnica, inventario por unidad, venta y logística de entrega en Colombia.

No es un ERP genérico ni un producto comercial.  
Es una **solución pragmática**, construida para resolver problemas reales de una operación en crecimiento.

---

## 2. Problema real que aborda

Antes de TradeHUB, la operación se gestionaba mediante:

- Hojas de cálculo independientes
- Conversaciones por WhatsApp
- Registros manuales no sincronizados

Esto generaba problemas críticos:

- Falta de trazabilidad por dispositivo
- Riesgo de pérdida de mercancía
- Errores en pagos y estados de venta
- Dificultad para coordinar inventario, ventas y logística
- Dependencia excesiva de la memoria humana

Excel y WhatsApp **dejaron de escalar** cuando el volumen de equipos y órdenes aumentó.

---

## 3. Visión general de la arquitectura

TradeHUB está construido bajo una arquitectura **low-code orientada a datos**, utilizando:

- **AppSheet** como capa de aplicación
- **Google Sheets** como base de datos relacional
- **Google Drive** como repositorio documental

Principios clave:

- Una unidad física = un registro único
- Separación clara entre datos maestros y transaccionales
- Control visual del estado operativo
- Acceso multiplataforma sin infraestructura propia

No hay servidores dedicados ni despliegues complejos.  
La prioridad es **operación, control y trazabilidad**.

---

## 4. Flujo real del negocio (end-to-end)

El sistema modela el flujo completo del negocio:

1. **Adquisición en el exterior**
   - Creación de lotes de compra
   - Registro de costos de adquisición

2. **Recepción y diagnóstico**
   - Ingreso individual por número de serie
   - Evaluación técnica del dispositivo

3. **Inventario operativo**
   - Clasificación por estado técnico
   - Asignación de ubicación y disponibilidad

4. **Proceso de venta**
   - Creación de orden de venta
   - Asociación de unidades específicas al pedido
   - Registro de pagos y comprobantes

5. **Logística y entrega**
   - Generación de envío
   - Seguimiento de estado hasta entrega final

Cada paso deja **huella digital** en el sistema.

---

## 5. Modelo de datos (conceptual)

Aunque utiliza Google Sheets, la base de datos fue diseñada bajo principios de **modelo relacional normalizado** (≈35 tablas).

Entidades clave:

- **productos**  
  Catálogo maestro de referencias y modelos

- **compras_lote**  
  Entrada masiva de equipos adquiridos

- **inventario**  
  Núcleo del sistema  
  Cada registro representa un dispositivo físico único con número de serie

- **reparaciones**  
  Historial técnico vinculado al inventario

- **orden_venta / orden_detalle**  
  Flujo comercial y asociación de unidades vendidas

- **pago_venta**  
  Control de pagos, métodos y estados

El diseño prioriza **integridad, trazabilidad y auditoría**.

---

## 6. Estados y semáforos operativos

### 6.1 Estados del inventario (ciclo técnico)

- En inspección
- En diagnóstico
- En reparación
- Disponible
- Vendido
- Baja técnica

Estos estados controlan cuándo una unidad puede entrar al flujo de ventas.

---

### 6.2 Estados de la venta (semáforo comercial)

- Creado (🟡)
- Aprobado (🔵)
- Enviado (🟠)
- Entregado (🟢)

El semáforo permite identificar cuellos de botella operativos en segundos.

---

## 7. Roles y control operativo

El acceso se gestiona mediante **roles y slices en AppSheet**:

- **Administrador**
  - Visión global y control financiero

- **Técnico**
  - Diagnóstico y estado del inventario

- **Vendedor**
  - Gestión de órdenes y pagos

- **Logística**
  - Despacho y seguimiento de envíos

Cada rol ve solo lo necesario para su función.

---

## 8. Decisiones técnicas clave

- **Low-code (AppSheet)**  
  → rapidez de implementación y adaptación

- **Google Sheets como backend**  
  → costo cero y alta disponibilidad

- **Trazabilidad por serial único**  
  → control real del activo físico

- **Soft deletes (`isActive`)**  
  → preservación de histórico y auditoría

- **Integración con Google Drive**  
  → evidencia técnica y financiera vinculada a datos

Estas decisiones priorizan **operación real sobre perfección teórica**.

---

## 9. Qué demuestra este proyecto

TradeHUB demuestra capacidad para:

- Modelar procesos reales de negocio
- Diseñar bases de datos normalizadas
- Traducir flujos físicos a sistemas digitales
- Implementar control visual de estados
- Construir soluciones escalables sin sobreingeniería

No es un demo académico.  
Es un sistema **usado en producción**.

---

## 10. Ámbitos de aplicación real

Este tipo de arquitectura es aplicable a:

- Reacondicionamiento de electrónicos
- Gestión de garantías
- Talleres técnicos
- Comercio de segunda mano
- Operaciones con inventario unitario
- Negocios con logística distribuida

El patrón es reusable, no el dominio específico.

---

## 11. Notas para el chatbot (respuestas esperadas)

**¿Cómo se evita la pérdida de equipos?**  
Mediante trazabilidad por número de serie desde el lote de compra hasta la venta final.

**¿Por qué no usar un ERP tradicional?**  
Por costo, complejidad y falta de flexibilidad frente a una operación pequeña pero dinámica.

**¿Qué valor técnico tiene usar AppSheet?**  
Permite enfocarse en modelado de datos y procesos sin fricción de infraestructura.

**¿Es un sistema terminado?**  
No. Es un sistema en evolución, diseñado para crecer por módulos.

---
