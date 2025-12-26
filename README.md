# SkySentinel Backend

Sistema Inteligente de Vigilancia Aeroespacial - Backend API

## Descripción

SkySentinel es un middleware geoespacial que conecta datos de aeronaves en tiempo real desde OpenSky Network API con agentes de Inteligencia Artificial. El backend está construido con FastAPI y sirve datos en formato GeoJSON optimizado para visualización en mapas y análisis con IA.

## Características

- **OpenSky Network Integration**: Datos de aeronaves en tiempo real
- **GeoJSON Output**: Formato optimizado para mapas y IA
- **FastAPI Backend**: API REST rápida y moderna
- **CORS Enabled**: Listo para integración con frontend
- **Regional Filtering**: Soporte para bounding box queries
- **Docker Ready**: Fácil despliegue en la nube

## Arquitectura

```
OpenSky Network API → SkySentinel Backend (FastAPI) → Frontend (Vue.js/Leaflet)
                                                     ↓
                                                 Gemini AI
```

## Instalación

### Requisitos

- Python 3.11+
- pip

### Setup Local

1. Crear entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno (opcional):
```bash
cp .env.example .env
# Editar .env con tus credenciales de OpenSky (opcional)
```

4. Ejecutar servidor:
```bash
python app/main.py
# O usar uvicorn directamente:
uvicorn app.main:app --reload
```

El servidor estará disponible en `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```

### Get Airspace Data
```
GET /api/v1/airspace?limit=50
```

Retorna datos de aeronaves en formato GeoJSON FeatureCollection.

**Parámetros:**
- `limit` (opcional): Número máximo de aeronaves a retornar (default: 50)

**Respuesta:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "icao24": "a12345",
        "callsign": "UAL123",
        "altitude": 10000,
        "velocity": 250,
        "heading": 180,
        "origin_country": "United States",
        "on_ground": false,
        "last_contact": 1234567890
      }
    }
  ],
  "metadata": {
    "total_aircraft": 50,
    "timestamp": 1234567890
  }
}
```

### Get Regional Airspace Data
```
GET /api/v1/airspace/region?min_lat=37&max_lat=38&min_lon=-123&max_lon=-122
```

Retorna datos de aeronaves dentro de una región específica (bounding box).

**Parámetros:**
- `min_lat`: Latitud mínima
- `max_lat`: Latitud máxima
- `min_lon`: Longitud mínima
- `max_lon`: Longitud máxima

## Docker

### Build
```bash
docker build -t skysentinel-backend .
```

### Run
```bash
docker run -p 8000:8000 skysentinel-backend
```

## Despliegue en la Nube

### Google Cloud Run (Recomendado)

1. Build y push a Container Registry:
```bash
gcloud builds submit --tag gcr.io/[PROJECT-ID]/skysentinel-backend
```

2. Deploy a Cloud Run:
```bash
gcloud run deploy skysentinel-backend \
  --image gcr.io/[PROJECT-ID]/skysentinel-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS App Runner

1. Conectar con GitHub
2. Configurar auto-deploy desde el repositorio
3. Especificar puerto 8000

## Integración con Frontend

El backend está diseñado para integrarse con el proyecto Vue.js existente:

```javascript
// En tu componente Vue
async function fetchAirspaceData() {
  const response = await fetch('http://localhost:8000/api/v1/airspace?limit=50');
  const geojson = await response.json();

  // Usar con Leaflet
  L.geoJSON(geojson).addTo(map);
}
```

## Próximas Características

- [ ] Geofencing: Zonas de exclusión aérea
- [ ] WebSocket support para updates en tiempo real
- [ ] Filtros avanzados (altitud, velocidad, tipo de aeronave)
- [ ] Cache de datos para reducir llamadas a OpenSky API
- [ ] Autenticación y rate limiting

## Tecnologías

- **FastAPI**: Framework web moderno y rápido
- **OpenSky Network API**: Fuente de datos de aeronaves
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **Pydantic**: Validación de datos
- **Python 3.11+**: Lenguaje de programación

## Licencia

MIT

## Autor

Proyecto SkySentinel - Sistema Inteligente de Vigilancia Aeroespacial
