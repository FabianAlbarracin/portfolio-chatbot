# Sistema Experimental de Telemetría Resiliente 

## 1. Qué es este proyecto

Este proyecto es un **sistema experimental de ingesta, procesamiento y visualización de telemetría**, diseñado para operar en **escenarios de conectividad limitada, intermitente o de alta latencia**.

No es un producto comercial ni un sistema productivo final.  
Funciona como un **laboratorio técnico funcional**, orientado a validar **patrones reales de arquitectura distribuida**, especialmente:

- Arquitecturas **event-driven (dirigida por eventos)**
    
- Uso de **MQTT como transporte resiliente**
    
- Backends **tolerantes a fallos**
    
- Integración de datos técnicos en **plataformas low-code (Appian)**
    

El foco del proyecto no es el hardware ni la visualización, sino el **diseño del flujo completo y sus decisiones técnicas**.

---

## 2. Problema que aborda

En escenarios reales como IoT, telemetría remota o comunicaciones satelitales, los sistemas enfrentan:

- Conectividad intermitente
    
- Alta latencia
    
- Pérdida de paquetes
    
- Mensajes incompletos o mal formados
    

Los enfoques tradicionales (HTTP síncrono, procesamiento inmediato, validación estricta) **no funcionan bien** en estos contextos.

Este proyecto explora cómo diseñar un sistema que:

- **No pierda datos**
    
- **Tolere errores sin detenerse**
    
- **Separe ingestión de procesamiento**
    
- **Permita análisis posterior incluso si algo falla**
    

---

## 3. Visión general de la arquitectura

El sistema sigue un enfoque **event-driven**, con desacoplamiento entre capas:

1. Un dispositivo físico genera eventos
    
2. Los eventos se transportan vía **MQTT**
    
3. Un backend los recibe y persiste
    
4. Los datos se exponen mediante una **API REST**
    
5. Appian consume la API y visualiza la información
    

### Principios de diseño

- Priorizar **resiliencia sobre simplicidad**
    
- Persistir siempre antes de procesar
    
- Aislar errores por etapa
    
- Mantener trazabilidad completa
    
- Permitir reprocesamiento futuro
    

---

## 4. Origen del evento (hardware)

### Dispositivo de prueba

- Microcontrolador **ESP32**
    
- Módulo de comunicación **LoRa**
    
- Antena externa
    

### Rol del hardware

El hardware actúa únicamente como **fuente de eventos**.

Simula condiciones reales como:

- Latencia
    
- Conectividad intermitente
    
- Envíos no continuos
    

El hardware **no es el foco del proyecto**, sino el punto de entrada para validar el pipeline completo.

---

## 5. Transporte de mensajes – MQTT

### Broker

- **TinyGS**
    
- MQTT sobre **TLS**
    

### Por qué MQTT

- Comunicación asincrónica
    
- Bajo consumo
    
- Manejo natural de conexiones inestables
    
- Actúa como **buffer entre el mundo físico y el backend**
    

### Formato del mensaje

- Payload en JSON
    
- Incluye:
    
    - Parámetros de transmisión (freq, bw, sf, pwr, etc.)
        
    - Metadatos del satélite (nombre, NORAD)
        
    - Información del enlace
        

MQTT desacopla completamente el origen del evento del procesamiento posterior.

---

## 6. Backend / API

### 6.1 Tecnologías utilizadas

- Python 3
    
- Flask (API REST)
    
- Paho MQTT Client
    
- SQLite (modo WAL)
    
- TLS para MQTT
    
- UUID para trazabilidad de mensajes
    

---

### 6.2 Rol del backend

El backend cumple **tres funciones críticas**:

1. Ingestar mensajes MQTT
    
2. Preservar datos **sin pérdida**
    
3. Exponer datos estructurados vía REST
    

El backend está diseñado para **no fallar ante datos defectuosos**.

---

### 6.3 Flujo interno del backend

#### Paso 1 – Recepción del mensaje

- El cliente MQTT recibe el mensaje
    
- Se genera un `id_message` único (UUID)
    
- Se registra metadata básica
    

---

#### Paso 2 – Persistencia RAW (obligatoria)

Todo mensaje recibido se guarda **siempre**, sin excepción.

Incluso si:

- No es UTF-8
    
- No es JSON
    
- El parseo falla
    
- Contiene errores de formato
    

Tabla: `MQTT_RAW_MESSAGES`

Esto garantiza:

- Auditabilidad total
    
- Cero pérdida de datos
    
- Posibilidad de reprocesamiento futuro
    

---

#### Paso 3 – Validación y parsing

- Se intenta decodificar el payload
    
- Se valida JSON
    
- Se verifica estructura esperada
    

Los errores:

- Se registran
    
- No detienen el sistema
    
- No bloquean otros mensajes
    

---

#### Paso 4 – Persistencia estructurada

Si el mensaje es válido:

- Se normaliza
    
- Se inserta en la tabla de telemetría
    
- Se marca el RAW como `parse_ok = 1`
    

Tabla: `TGSAS_W1644_DATOS_TELEMETRIA`

---

## 7. Modelo de datos (conceptual)

### RAW Messages

Contiene:

- Payload original
    
- Texto o base64
    
- Flags de estado (`is_json`, `parse_ok`)
    
- Detalle de error (si existe)
    
- Timestamps
    

### Telemetría estructurada

Contiene:

- Satélite
    
- Frecuencia
    
- Potencia
    
- Parámetros de transmisión
    
- Timestamp normalizado
    

### Por qué separar RAW y Telemetría

- Permite reprocesar datos
    
- Facilita debugging
    
- Aísla errores
    
- Permite cambiar reglas sin perder histórico
    

---

## 8. API REST

El backend expone endpoints REST para:

- Métricas agregadas
    
- Conteos diarios y semanales
    
- Rankings por satélite
    
- Series temporales
    
- Consulta de datos crudos filtrados
    

Ejemplos:

- `/stats/top-satellites-weekly`
    
- `/stats/weekly`
    
- `/data/daily`
    

La API está pensada para:

- Appian
    
- Clientes externos
    
- Dashboards futuros
    

---

## 9. Integración con Appian

### Tipo

- REST Integration Object
    

### Características

- Método: GET
    
- Response Type: JSON
    
- Parámetros dinámicos (`limit`, fechas)
    

Appian **no procesa telemetría cruda**.

Consume datos ya procesados y se enfoca en:

- Visualización
    
- Análisis
    
- Presentación
    

---

## 10. Visualización en Appian (SAIL)

### Dashboards

- Métricas agregadas
    
- Rankings
    
- Series temporales
    

### Ventajas

- Abstracción total de la complejidad técnica
    
- Separación clara entre:
    
    - procesamiento (backend)
        
    - presentación (Appian)
        
- Enfoque en monitoreo y decisión
    

---

## 11. Decisiones técnicas clave (para recordar)

- MQTT en lugar de HTTP → resiliencia
    
- Persistencia RAW obligatoria → cero pérdida de datos
    
- SQLite WAL → simplicidad + concurrencia
    
- API REST desacoplada → reutilización
    
- Appian solo consume → bajo acoplamiento