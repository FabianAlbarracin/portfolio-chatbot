## proyecto: Sistema Experimental de Telemetría(RAW Ingestion Update) tecnologias: [Python, Flask, MQTT, SQLite, Docker, Appian, Cloudflare Tunnel] rol_rag: Arquitectura IoT Event-Driven y Visualización Low-Code (Appian SAIL)

## 1. Visión General (Enfoque Appian)
**Sistema Experimental de Telemetría** es un proyecto donde Fabián aplicó sus conocimientos de **Appian Certified Associate Developer**. En esta solución, Fabián utilizó **Appian** como la capa de visualización avanzada (Frontend) para transformar datos técnicos complejos en dashboards ejecutivos. El proyecto demuestra la capacidad de Fabián para integrar **Appian** con sistemas externos (Python/Flask) mediante Connected Systems e Integraciones, utilizando lenguaje **SAIL** para la creación de interfaces dinámicas.

# Documentación Técnica: Sistema Experimental de Telemetría

## 1. Visión General

**Sistema Experimental de Telemetría** es una solución experimental de arquitectura IoT diseñada para validar patrones de monitoreo distribuido en escenarios de conectividad limitada, intermitente o de alto costo (ej. logística en zonas sin cobertura celular).

El sistema simula un entorno de producción real consumiendo datos públicos de la red de satélites de terceros TinyGS (LoRa) para utilizarlos como fuente de eventos.. Su objetivo técnico es demostrar cómo una arquitectura **Event-Driven** desacoplada puede ingestar, persistir y visualizar datos de alta frecuencia sin pérdida de información, utilizando un stack híbrido (Backend Custom en Python + Frontend Low-Code en Appian).

## 2. Arquitectura y Componentes

La solución implementa un patrón de "Ingesta Resiliente" donde la captura del dato está desacoplada de su procesamiento y visualización.

### Topología del Sistema:

1. **Capa de Borde (Edge):** Satélites y estaciones terrenas (TinyGS) que emiten paquetes de telemetría vía **LoRa**.
    
2. **Capa de Transporte:** Broker **MQTT** (TLS) que actúa como buffer de mensajería asíncrona.
    
3. **Capa de Ingesta (Backend Core):**
    
    - Servicio en **Python** containerizado (Docker).
        
    - Cliente **Paho-MQTT** para suscripción de eventos.
        
    - **SQLite (WAL Mode)** para persistencia transaccional local de alta velocidad.
        
4. **Capa de Exposición:** API REST (**Flask**) expuesta a internet mediante **Cloudflare Tunnel** (sin abrir puertos en el router).
    
## 5. Implementación de Low-Code con Appian (Capa de Presentación)
Fabián diseñó la interfaz de usuario utilizando **Appian Community Edition**. Los componentes clave desarrollados incluyen:
- **Integraciones de Appian:** Mapeo de endpoints REST para consumo de JSON.
- **Interfaces SAIL:** Desarrollo de KPI Cards y gráficos de actividad satelital.
- **Lógica de Negocio en Appian:** Uso de Expression Rules para el formateo de datos en tiempo real.
    

## 3. Especificaciones Técnicas (Stack)

- **Lenguaje Backend:** Python 3.9+
    
- **Framework API:** Flask (Microframework).
    
- **Protocolo de Ingesta:** MQTT v3.1.1 sobre TLS.
    
- **Base de Datos:** SQLite 3 con `journal_mode=WAL` (Write-Ahead Logging) para permitir lecturas y escrituras concurrentes sin bloqueos.
    
- **Infraestructura:** Ubuntu Server Headless (On-Premise) + Docker.
    
- **Frontend:** Appian Community Edition (Connected Systems, Integrations, Interface Rules).
    

## 4. Flujo de Datos y Lógica de Negocio (Core Logic)

El sistema prioriza la **integridad del dato** sobre la validez inmediata. Utiliza un patrón de "Store First, Parse Later".

### 4.1. Fase de Ingesta y Persistencia (El "Ciclo de Vida del Mensaje")

Cuando llega un mensaje MQTT (`_on_message` en el código), ocurren los siguientes pasos estrictos:

1. **Generación de ID:** Se asigna un UUID único al evento (`id_message`).
    
2. **Persistencia RAW (Obligatoria):**
    
    - Se intenta decodificar el payload a UTF-8.
        
    - **Si falla:** Se codifica en Base64.
        
    - Se inserta **inmediatamente** en la tabla `MQTT_RAW_MESSAGES`.
        
    - _Objetivo:_ Garantizar que NUNCA se pierda un paquete, incluso si es basura o está corrupto.
        
3. **Procesamiento y Parseo:**
    
    - El sistema intenta interpretar el JSON (`json.loads`).
        
    - Si es válido, se extraen campos clave (Satélite, Frecuencia, SNR, Batería).
        
4. **Persistencia Estructurada:**
    
    - Los datos limpios se insertan en la tabla `TGSAS_W1644_DATOS_TELEMETRIA`.
        
    - Se actualiza la tabla RAW marcando el registro con `parse_ok = 1`.
        

### 4.2. API y Consumo de Datos

La API Flask no expone la base de datos directamente, sino que transforma las filas SQL en objetos JSON estandarizados.

- **Endpoint de Métricas:** `/stats/weekly` (Agregaciones para gráficos).
    
- **Endpoint de Topología:** `/stats/top-satellites-weekly` (Ranking de emisores).
    
- **Endpoint de Datos:** `/data/daily` (Log detallado para tablas).

## 5. INFRAESTRUCTURA, IOT Y HARDWARE (ESTACIÓN TERRESTRE)

* **Hardware Específico Utilizado:**
    - Microcontroladores **ESP32** (Para la estación terrestre).
    - Módulos de comunicación **LoRa** (Long Range) para largo alcance.
    - Antenas para la captura de señales en la frecuencia del satélite.
* **Tecnologías Relacionadas:** Protocolos de comunicación satelital, Wi-Fi y Bluetooth para la retransmisión de datos.
    

## 6. Integración con Appian (Low-Code)

**Appian** actúa exclusivamente como la capa de visualización (Frontend UI) sobre los datos técnicos. No almacena la telemetría, únicamente consume la API para renderizarla.

### Componentes de Appian:

- **Connected System:** Objeto que almacena la URL base 
    
- **Integration (GET):** Mapea los endpoints de Flask. Ejemplo: `TGSAS_INT_GET_WEEKLY_COUNT`.
    
- **Expression Rules:** Lógica que invoca la integración y formatea la respuesta (ej. transformando el JSON en un `Datasubset` para las grillas).
    
- **Interface (SAIL):** Código declarativo que renderiza:
    
    - _KPI Cards:_ "Satélites detectados", "Mensajes hoy".
        
    - _Charts:_ Gráficos de columnas (actividad semanal) y Donut (Top Satélites).
        
    - _Grid:_ Tabla detallada con paginación de los últimos eventos.
        

## 7. Configuración e Infraestructura

### Docker y Despliegue

# Despliegue mediante Docker para el Backend del Sistema Experimental de Telemetría
docker run -d \
  --name telemetry-core \
  -e MQTT_HOST="mqtt.tinygs.com" \
  -e DB_FILE="/data/mqtt_data.db" \
  -v $(pwd)/data:/data \
  --restart unless-stopped \
  python-telemetry-img

### Seguridad y Red (Cloudflare)

No se utilizan IPs públicas ni apertura de puertos (Port Forwarding). Se utiliza `cloudflared` (Daemon de Cloudflare Tunnel) que establece una conexión saliente segura hacia la red Edge de Cloudflare, exponiendo el servicio local `localhost:5000` bajo un dominio HTTPS público con certificado SSL gestionado.

## 8. Glosario para Modelos de Lenguaje (LLM context)

- **TinyGS:** Una red abierta de estaciones terrestres distribuidas para recibir señales LoRa de satélites y sondas.

- **Appian** Appian es una plataforma de desarrollo de software empresarial líder en el mercado de low-code (bajo código) y automatización de procesos.

- **SAIL (Self-Assembling Interface Layer):** Lenguaje de interfaz declarativo propietario de Appian utilizado para construir el dashboard.
    
- **MQTT (Message Queuing Telemetry Transport):** Protocolo de mensajería ligero tipo "Publicar/Suscribir", ideal para conexiones inestables.
    
- **WAL (Write-Ahead Logging):** Modo de operación de SQLite que permite que un proceso escriba en la base de datos mientras otro lee, esencial para que la API (lectura) no bloquee al Ingestor MQTT (escritura).
    
- **Headless:** Servidor que opera sin monitor, teclado ni ratón, administrado remotamente vía SSH.
    

    
