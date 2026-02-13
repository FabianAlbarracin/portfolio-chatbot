**Proyecto: FabsLabs (Home Lab Server)**

### Tecnologías

* **Sistema Operativo:** Ubuntu Server (Headless/LTS).
* **Virtualización/Contenedores:** Docker Engine, Docker Compose.
* **Gestión y Orquestación:** Portainer, Systemd.
* **Redes y Seguridad:** Cloudflare Tunnel (`cloudflared`), SSH (Secure Shell), UFW (Uncomplicated Firewall).
* **Scripting/Automatización:** Bash, Cron jobs.
* **Servicios Alojados:** Nginx, Python (Flask), Bases de datos (SQLite/MariaDB), Broker MQTT.

### Tipo

Infraestructura de Servidor On-Premise (Homelab) y entorno de prácticas DevOps para despliegue de microservicios.

### Problema que resuelve

La necesidad de un entorno de despliegue persistente, controlado y económico para probar aplicaciones en condiciones cercanas a producción. Resuelve la limitación de desarrollar únicamente en `localhost` al permitir la exposición segura de servicios a internet para pruebas de integración y acceso remoto, eliminando los costos recurrentes de un VPS en la nube y mitigando los riesgos de seguridad asociados a la apertura de puertos en redes domésticas.

### Arquitectura / Implementación técnica

**Rol del desarrollador**
Responsable de la administración de sistemas (SysAdmin) y operaciones de desarrollo (DevOps):

* **Aprovisionamiento:** Instalación y configuración del sistema operativo y endurecimiento (hardening) del servidor.
* **Gestión de Contenedores:** Orquestación de servicios mediante Docker Compose y mantenimiento de volúmenes persistentes.
* **Ingeniería de Red:** Configuración de túneles cifrados y gestión de DNS.
* **Automatización:** Creación de scripts en Bash para tareas de mantenimiento, actualizaciones y copias de seguridad.

**Backend (Host)**
El núcleo es una instancia de **Ubuntu Server** ejecutándose en modo *headless* (sin interfaz gráfica) para optimizar recursos. La administración se realiza exclusivamente vía **SSH** con autenticación basada en claves (key-based authentication), deshabilitando el acceso por contraseña para mayor seguridad.

**Capa de Aplicación (Docker)**
Todos los servicios (API de Telemetría, Asistente RAG, Bases de Datos) se ejecutan como microservicios aislados dentro de contenedores **Docker**.

* **Portainer:** Se utiliza como interfaz de gestión visual para monitorear el estado de los contenedores, visualizar logs en tiempo real y gestionar imágenes y redes internas.
* **Persistencia:** Los datos críticos se gestionan mediante volúmenes de Docker mapeados al sistema de archivos del host, facilitando las copias de seguridad.

**Redes y Seguridad**
La exposición de servicios a internet evita el tradicional *Port Forwarding*. Se implementa **Cloudflare Tunnel**, que establece una conexión saliente cifrada desde el servidor hacia la red edge de Cloudflare.

* Esto permite servir aplicaciones locales bajo dominios HTTPS públicos con certificados SSL gestionados automáticamente.
* El firewall **UFW** está configurado para denegar todo el tráfico entrante no esencial, permitiendo solo conexiones SSH desde IPs autorizadas o red local.

**Flujo de Despliegue**

1. Desarrollo de la aplicación en entorno local.
2. Definición de infraestructura en archivos `docker-compose.yml`.
3. Transferencia o pull de código/imágenes al servidor FabsLabs.
4. Despliegue de contenedores y mapeo de puertos al servicio de túnel.

### Funcionalidades clave

* **Entorno de Producción Simulado:** Capacidad para ejecutar servicios 24/7 con gestión de reinicios automáticos (`restart: always`).
* **Exposición Segura (Zero Trust):** Acceso a aplicaciones internas desde cualquier lugar sin exponer la IP pública del hogar ni abrir puertos en el router.
* **Gestión Centralizada:** Control total de recursos (CPU, RAM, Almacenamiento) y logs a través de Portainer.
* **Aislamiento de Servicios:** Cada aplicación corre en su propio entorno, evitando conflictos de dependencias.

### Resultados / Impacto

* Alojamiento estable y seguro del backend para el sistema de **Telemetría Satelital** y el **Portfolio RAG Assistant**.
* Reducción del 100% en costos de infraestructura en la nube (AWS/Azure/DigitalOcean) para proyectos personales.
* Entorno funcional para experimentar con configuraciones de red, proxies inversos y bases de datos sin riesgo para el equipo de trabajo principal.

### Limitaciones o mejoras futuras

* **Redundancia de Hardware:** Actualmente es un nodo único (Single Point of Failure). Un fallo de hardware detiene todos los servicios.
* **Backup Off-site:** Implementar una estrategia automatizada de copias de seguridad (regla 3-2-1) hacia un almacenamiento en la nube (ej. AWS S3 o Google Drive) para recuperación ante desastres.
* **Monitoreo Avanzado:** Integrar un stack de observabilidad como Prometheus y Grafana para métricas detalladas del hardware y contenedores.