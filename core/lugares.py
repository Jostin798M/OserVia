"""Lugares para el autocompletado de los buscadores: catálogo propio más los lugares de las ofertas publicadas."""
import unicodedata

# (ciudad, código IATA, país, latitud, longitud)
CATALOGO = [
    ('Guayaquil', 'GYE', 'Ecuador', -2.157, -79.884), ('Quito', 'UIO', 'Ecuador', -0.129, -78.358),
    ('Cuenca', 'CUE', 'Ecuador', -2.889, -78.984), ('Manta', 'MEC', 'Ecuador', -0.946, -80.679),
    ('Loja', 'LOH', 'Ecuador', -3.995, -79.372), ('Esmeraldas', 'ESM', 'Ecuador', 0.978, -79.627),
    ('Galápagos', 'GPS', 'Ecuador', -0.454, -90.266), ('Bogotá', 'BOG', 'Colombia', 4.702, -74.147),
    ('Medellín', 'MDE', 'Colombia', 6.164, -75.423), ('Cali', 'CLO', 'Colombia', 3.543, -76.382),
    ('Cartagena', 'CTG', 'Colombia', 10.442, -75.513), ('Lima', 'LIM', 'Perú', -12.022, -77.114),
    ('Cusco', 'CUZ', 'Perú', -13.536, -71.939), ('La Paz', 'LPB', 'Bolivia', -16.513, -68.192),
    ('Santiago', 'SCL', 'Chile', -33.393, -70.786), ('Buenos Aires', 'EZE', 'Argentina', -34.822, -58.536),
    ('Montevideo', 'MVD', 'Uruguay', -34.838, -56.031), ('São Paulo', 'GRU', 'Brasil', -23.432, -46.469),
    ('Río de Janeiro', 'GIG', 'Brasil', -22.810, -43.251), ('Caracas', 'CCS', 'Venezuela', 10.601, -66.991),
    ('Ciudad de Panamá', 'PTY', 'Panamá', 9.071, -79.383), ('San José', 'SJO', 'Costa Rica', 9.994, -84.209),
    ('Ciudad de México', 'MEX', 'México', 19.436, -99.072), ('Cancún', 'CUN', 'México', 21.037, -86.877),
    ('Punta Cana', 'PUJ', 'República Dominicana', 18.567, -68.364),
    ('Santo Domingo', 'SDQ', 'República Dominicana', 18.430, -69.669), ('La Habana', 'HAV', 'Cuba', 22.989, -82.409),
    ('Miami', 'MIA', 'Estados Unidos', 25.796, -80.287), ('Fort Lauderdale', 'FLL', 'Estados Unidos', 26.072, -80.153),
    ('Orlando', 'MCO', 'Estados Unidos', 28.429, -81.309), ('Nueva York', 'JFK', 'Estados Unidos', 40.641, -73.778),
    ('Los Ángeles', 'LAX', 'Estados Unidos', 33.942, -118.408), ('Houston', 'IAH', 'Estados Unidos', 29.984, -95.341),
    ('Atlanta', 'ATL', 'Estados Unidos', 33.640, -84.427), ('Toronto', 'YYZ', 'Canadá', 43.677, -79.625),
    ('Montreal', 'YUL', 'Canadá', 45.470, -73.741), ('Madrid', 'MAD', 'España', 40.494, -3.567),
    ('Barcelona', 'BCN', 'España', 41.297, 2.083), ('París', 'CDG', 'Francia', 49.010, 2.548),
    ('Londres', 'LHR', 'Reino Unido', 51.470, -0.454), ('Roma', 'FCO', 'Italia', 41.800, 12.239),
    ('Ámsterdam', 'AMS', 'Países Bajos', 52.310, 4.768), ('Fráncfort', 'FRA', 'Alemania', 50.038, 8.562),
    ('Lisboa', 'LIS', 'Portugal', 38.774, -9.134), ('Estambul', 'IST', 'Turquía', 41.275, 28.752),
    ('Dubái', 'DXB', 'Emiratos Árabes Unidos', 25.253, 55.365), ('Tokio', 'NRT', 'Japón', 35.772, 140.393),
    ('Bangkok', 'BKK', 'Tailandia', 13.690, 100.750),
]


def normalizar(texto):
    """Minúsculas y sin tildes: «Panamá» y «panama» son lo mismo."""
    texto = unicodedata.normalize('NFD', texto or '')
    return ''.join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def _base(texto):
    """«Guayaquil (GYE)» y «Guayaquil, Ecuador» -> «guayaquil»."""
    return normalizar(texto.split('(')[0].split(',')[0])


def coincide(valor, busqueda):
    """Acepta el nombre, el código o el texto exacto de una sugerencia, con o sin tildes."""
    valor, completa, base = normalizar(valor), normalizar(busqueda), _base(busqueda)
    return completa in valor or bool(base and base in valor)


def sugerencias(ofertas, campo, con_codigo=True):
    """Lista para el autocompletado; primero los lugares que tienen ofertas publicadas."""
    conteo = {}
    for o in ofertas:
        valor = getattr(o, campo)
        if valor:
            conteo.setdefault(_base(valor), [valor, 0])[1] += 1
    lugares = []
    for ciudad, iata, pais, lat, lon in CATALOGO:
        _, cantidad = conteo.pop(normalizar(ciudad), (None, 0))
        lugares.append({'valor': f'{ciudad} ({iata})' if con_codigo else f'{ciudad}, {pais}', 'detalle': pais,
                        'ofertas': cantidad, 'lat': lat, 'lon': lon})
    lugares += [{'valor': valor, 'detalle': '', 'ofertas': cantidad} for valor, cantidad in conteo.values()]
    return sorted(lugares, key=lambda l: -l['ofertas'])
