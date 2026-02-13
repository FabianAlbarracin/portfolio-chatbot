**Proyecto: Sistema de Telemetría Satelital Resiliente**

### Tecnologías

- **Hardware / IoT:** ESP32, Módulos LoRa (433/915 MHz), TinyGS Network.
- **Protocolos:** MQTT v3.1.1 (sobre TLS), LoRaWAN (Capa física).
- **Backend:** Python 3.9+, Flask (Microframework), Paho-MQTT.
- **Base de Datos:** SQLite 3 (Modo WAL - Write-Ahead Logging).
- **Infraestructura:** Docker, Linux (Ubuntu Server Headless), Cloudflare Tunnel (`cloudflared`).
- **Frontend / BI:** Appian (SAIL, Connected Systems, Integrations).
- **Formatos:** JSON, Base64.

### Tipo

Sistema de ingesta, procesamiento y visualización de datos IoT basado en arquitectura orientada a eventos (Event-Driven Architecture), diseñado para entornos de conectividad intermitente.

### Problema que resuelve

La captura confiable de datos de telemetría en escenarios de alta latencia y conectividad inestable (como enlaces satelitales o zonas remotas sin cobertura celular). Resuelve específicamente la pérdida de datos durante la transmisión y la dificultad de integrar hardware de radiofrecuencia (LoRa) con plataformas de gestión empresarial modernas, garantizando auditabilidad completa de la señal original.

### Arquitectura / Implementación técnica

**Backend**
Desarrollado en **Python**, opera como un servicio demonio que gestiona dos hilos principales:
1. **Ingestor MQTT:** Cliente suscripto a tópicos de la red TinyGS con lógica de reintento y manejo de excepciones para evitar caídas ante datos corruptos.
2. **API REST (Flask):** Expone endpoints de lectura (`GET`) para consultar métricas y registros, transformando datos relacionales en objetos JSON estandarizados.

**Frontend**
Implementado en **Appian** como capa de visualización. Utiliza objetos *Integration* y *Connected Systems* para consumir la API REST. No almacena datos persistentes, limitándose a la renderización de Dashboards en interfaces SAIL para monitoreo de KPIs y series temporales.

**Base de datos**
**SQLite** configurado en modo **WAL (Write-Ahead Logging)** para permitir concurrencia entre escritura masiva (Ingestor) y lectura (API). Modelo de datos con estrategia de doble persistencia:
- **Tabla RAW (`MQTT_RAW_MESSAGES`):** Almacena el payload original exacto (Base64/UTF-8) y un UUID.
- **Tabla Estructurada (`TELEMETRIA_DATA`):** Almacena datos parseados y normalizados (Satélite, Frecuencia, SNR, Batería) tras validación JSON.

**Infraestructura**
Ejecución en entorno **Linux Headless** dentro de contenedores **Docker**. La exposición a internet se gestiona mediante **Cloudflare Tunnel**, estableciendo una conexión saliente segura hacia un dominio HTTPS público, sin apertura de puertos locales ni exposición de IP pública.

**Integraciones**
- **TinyGS Network:** Fuente de eventos externos vía MQTT.
- **Appian:** Plataforma Low-Code para la capa de presentación y consumo de datos.

**Flujo de datos**
1. **Recepción Física:** Estación terrena recibe paquete LoRa de satélite en órbita baja.
2. **Transporte:** Encapsulamiento en mensaje MQTT y envío al broker.
3. **Ingesta:** Servicio Python recibe evento, genera UUID y persiste en tabla RAW.
4. **Procesamiento:** Decodificación de JSON, extracción de métricas e inserción en tabla Estructurada. Marcado de registro RAW como procesado.
5. **Visualización:** Appian solicita datos a API Flask y renderiza indicadores.

### Funcionalidades clave

- **Persistencia Resiliente (Raw-First):** Capacidad de almacenar mensajes corruptos o no estructurados para auditoría y reprocesamiento futuro.
    
- **Decodificación Asíncrona:** El fallo en el parseo de un mensaje no detiene el flujo de ingesta de los siguientes.
    
- **Exposición Segura:** API accesible públicamente vía HTTPS sin comprometer la seguridad de la red local (Homelab).
    
- **Visualización Low-Code:** Dashboards en Appian SAIL que muestran KPIs (mensajes/hora, satélites activos) y gráficos de series temporales.
    
- **Trazabilidad Unitaria:** Cada paquete de telemetría es rastreable desde su recepción física hasta su visualización mediante identificadores únicos.
    

### Resultados / Impacto

- Implementación exitosa de un sistema funcional capaz de recibir y procesar señales débiles de satélites reales a distancias de 400-600 km.
    
- Demostración práctica de integración entre microcontroladores de bajo costo y plataformas empresariales (Appian).
    
- Creación de un entorno de laboratorio "Homelab" estable y replicable para pruebas de latencia y telemetría distribuida.
    

#### Competencias demostradas

- Diseño de arquitectura tolerante a fallos.
- Integración de protocolos de mensajería asíncrona.
- Manejo de concurrencia en base de datos ligera.
- Exposición segura de servicios en entornos domésticos (Homelab).
- Capacidad autodidacta en tecnologías IoT y RF.

### Limitaciones o mejoras futuras

- **Escalabilidad de la Base de Datos:** Limitaciones de rendimiento de SQLite ante escrituras masivas simultáneas; requiere migración a base de datos de series temporales (InfluxDB/TimescaleDB).
- **Dependencia de Red Externa:** Dependencia de la disponibilidad del broker público de TinyGS para recepción de paquetes globales.