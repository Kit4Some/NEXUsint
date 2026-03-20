import { create } from 'zustand';

import type {
  LiveFlight,
  MilitaryFlight,
  UAV,
  NewsArticle,
  Earthquake,
  FireHotspot,
  GPSJammingZone,
  SpaceWeather,
  WeatherRadar,
  StockData,
  OilData,
  Satellite,
  GDELTEvent,
  InternetOutage,
  KiwiSDR,
  Airport,
  ReferencePoint,
} from '@/types/livefeed';

interface LiveFeedState {
  // Data slices
  flights: LiveFlight[];
  militaryFlights: MilitaryFlight[];
  trackedFlights: LiveFlight[];
  uavs: UAV[];
  news: NewsArticle[];
  earthquakes: Earthquake[];
  fires: FireHotspot[];
  stocks: Record<string, StockData>;
  oil: Record<string, OilData>;
  gpsJamming: GPSJammingZone[];
  spaceWeather: SpaceWeather | null;
  weatherRadar: WeatherRadar | null;
  satellites: Satellite[];
  gdelt: GDELTEvent[];
  frontlines: unknown;
  internetOutages: InternetOutage[];
  kiwisdr: KiwiSDR[];
  airports: Airport[];
  militaryBases: ReferencePoint[];
  datacenters: ReferencePoint[];
  powerPlants: ReferencePoint[];
  sourceTimestamps: Record<string, string>;
  isActive: boolean;
  lastUpdated: string | null;

  // Setters
  setFlights: (flights: LiveFlight[]) => void;
  setMilitaryFlights: (flights: MilitaryFlight[]) => void;
  setTrackedFlights: (flights: LiveFlight[]) => void;
  setUavs: (uavs: UAV[]) => void;
  setNews: (news: NewsArticle[]) => void;
  setEarthquakes: (earthquakes: Earthquake[]) => void;
  setFires: (fires: FireHotspot[]) => void;
  setStocks: (stocks: Record<string, StockData>) => void;
  setOil: (oil: Record<string, OilData>) => void;
  setGpsJamming: (zones: GPSJammingZone[]) => void;
  setSpaceWeather: (data: SpaceWeather | null) => void;
  setWeatherRadar: (data: WeatherRadar | null) => void;
  setSatellites: (satellites: Satellite[]) => void;
  setGdelt: (gdelt: GDELTEvent[]) => void;
  setFrontlines: (frontlines: unknown) => void;
  setInternetOutages: (outages: InternetOutage[]) => void;
  setKiwisdr: (kiwisdr: KiwiSDR[]) => void;
  setAirports: (airports: Airport[]) => void;
  setMilitaryBases: (bases: ReferencePoint[]) => void;
  setDatacenters: (datacenters: ReferencePoint[]) => void;
  setPowerPlants: (plants: ReferencePoint[]) => void;
  setSourceTimestamps: (timestamps: Record<string, string>) => void;
  setActive: (active: boolean) => void;

  // API actions
  startLiveFeed: () => Promise<void>;
  stopLiveFeed: () => Promise<void>;
  pollLiveData: () => Promise<void>;
}

let _pollTimer: ReturnType<typeof setInterval> | null = null;

export const useLiveFeedStore = create<LiveFeedState>((set, get) => ({
  // Initial state
  flights: [],
  militaryFlights: [],
  trackedFlights: [],
  uavs: [],
  news: [],
  earthquakes: [],
  fires: [],
  stocks: {},
  oil: {},
  gpsJamming: [],
  spaceWeather: null,
  weatherRadar: null,
  satellites: [],
  gdelt: [],
  frontlines: null,
  internetOutages: [],
  kiwisdr: [],
  airports: [],
  militaryBases: [],
  datacenters: [],
  powerPlants: [],
  sourceTimestamps: {},
  isActive: false,
  lastUpdated: null,

  // Setters
  setFlights: (flights) =>
    set({ flights, lastUpdated: new Date().toISOString() }),

  setMilitaryFlights: (militaryFlights) =>
    set({ militaryFlights, lastUpdated: new Date().toISOString() }),

  setTrackedFlights: (trackedFlights) =>
    set({ trackedFlights, lastUpdated: new Date().toISOString() }),

  setUavs: (uavs) =>
    set({ uavs, lastUpdated: new Date().toISOString() }),

  setNews: (news) =>
    set({ news, lastUpdated: new Date().toISOString() }),

  setEarthquakes: (earthquakes) =>
    set({ earthquakes, lastUpdated: new Date().toISOString() }),

  setFires: (fires) =>
    set({ fires, lastUpdated: new Date().toISOString() }),

  setStocks: (stocks) =>
    set({ stocks, lastUpdated: new Date().toISOString() }),

  setOil: (oil) =>
    set({ oil, lastUpdated: new Date().toISOString() }),

  setGpsJamming: (gpsJamming) =>
    set({ gpsJamming, lastUpdated: new Date().toISOString() }),

  setSpaceWeather: (spaceWeather) =>
    set({ spaceWeather, lastUpdated: new Date().toISOString() }),

  setWeatherRadar: (weatherRadar) =>
    set({ weatherRadar, lastUpdated: new Date().toISOString() }),

  setSatellites: (satellites) =>
    set({ satellites, lastUpdated: new Date().toISOString() }),

  setGdelt: (gdelt) =>
    set({ gdelt, lastUpdated: new Date().toISOString() }),

  setFrontlines: (frontlines) =>
    set({ frontlines, lastUpdated: new Date().toISOString() }),

  setInternetOutages: (internetOutages) =>
    set({ internetOutages, lastUpdated: new Date().toISOString() }),

  setKiwisdr: (kiwisdr) =>
    set({ kiwisdr, lastUpdated: new Date().toISOString() }),

  setAirports: (airports) =>
    set({ airports, lastUpdated: new Date().toISOString() }),

  setMilitaryBases: (militaryBases) =>
    set({ militaryBases, lastUpdated: new Date().toISOString() }),

  setDatacenters: (datacenters) =>
    set({ datacenters, lastUpdated: new Date().toISOString() }),

  setPowerPlants: (powerPlants) =>
    set({ powerPlants, lastUpdated: new Date().toISOString() }),

  setSourceTimestamps: (sourceTimestamps) =>
    set({ sourceTimestamps, lastUpdated: new Date().toISOString() }),

  setActive: (isActive) => set({ isActive }),

  // Poll live data via REST (fallback when WebSocket/Celery isn't pushing)
  pollLiveData: async () => {
    try {
      const { liveFeed } = await import('@/services/api');

      const [fastRes, slowRes] = await Promise.allSettled([
        liveFeed.getFast(),
        liveFeed.getSlow(),
      ]);

      const now = new Date().toISOString();

      if (fastRes.status === 'fulfilled' && fastRes.value) {
        const fast = fastRes.value;
        const allFlights = [
          ...(fast.commercial_flights || []),
          ...(fast.private_jets || []),
          ...(fast.private_flights || []),
        ];
        if (allFlights.length > 0) set({ flights: allFlights as LiveFlight[] });
        if (fast.tracked_flights?.length) set({ trackedFlights: fast.tracked_flights as LiveFlight[] });
        if (fast.military_flights?.length) set({ militaryFlights: fast.military_flights as MilitaryFlight[] });
        if (fast.uavs?.length) set({ uavs: fast.uavs as UAV[] });
        if (fast.gps_jamming?.length) set({ gpsJamming: fast.gps_jamming as GPSJammingZone[] });
        if (fast.satellites?.length) set({ satellites: fast.satellites as Satellite[] });
        if (fast.freshness) set({ sourceTimestamps: fast.freshness });
      }

      if (slowRes.status === 'fulfilled' && slowRes.value) {
        const slow = slowRes.value;
        if (slow.news?.length) set({ news: slow.news as NewsArticle[] });
        if (slow.earthquakes?.length) set({ earthquakes: slow.earthquakes as Earthquake[] });
        if (slow.fires?.length) set({ fires: slow.fires as FireHotspot[] });
        if (slow.stocks && Object.keys(slow.stocks).length) set({ stocks: slow.stocks as Record<string, StockData> });
        if (slow.oil && Object.keys(slow.oil).length) set({ oil: slow.oil as Record<string, OilData> });
        if (slow.weather) set({ weatherRadar: slow.weather as WeatherRadar });
        if (slow.space_weather) set({ spaceWeather: slow.space_weather as SpaceWeather });
        if (slow.gdelt?.length) set({ gdelt: slow.gdelt as GDELTEvent[] });
        if (slow.frontlines) set({ frontlines: slow.frontlines });
        if (slow.internet_outages?.length) set({ internetOutages: slow.internet_outages as InternetOutage[] });
        if (slow.kiwisdr?.length) set({ kiwisdr: slow.kiwisdr as KiwiSDR[] });
        if (slow.airports?.length) set({ airports: slow.airports as Airport[] });
        if (slow.military_bases?.length) set({ militaryBases: slow.military_bases as ReferencePoint[] });
        if (slow.datacenters?.length) set({ datacenters: slow.datacenters as ReferencePoint[] });
        if (slow.power_plants?.length) set({ powerPlants: slow.power_plants as ReferencePoint[] });
        if (slow.freshness) set({ sourceTimestamps: slow.freshness });
      }

      set({ lastUpdated: now });
    } catch (error) {
      // Silently fail — data will arrive via WebSocket if Celery is running
    }
  },

  // API actions
  startLiveFeed: async () => {
    try {
      const { liveFeed } = await import('@/services/api');
      await liveFeed.start();
      set({ isActive: true });

      // Start REST polling as fallback (every 15 seconds)
      // WebSocket updates will also arrive if Celery workers are running
      if (_pollTimer) clearInterval(_pollTimer);
      // Initial poll immediately
      get().pollLiveData();
      _pollTimer = setInterval(() => {
        get().pollLiveData();
      }, 15_000);
    } catch (error) {
      console.error('[LiveFeed] Failed to start:', error);
    }
  },

  stopLiveFeed: async () => {
    try {
      const { liveFeed } = await import('@/services/api');
      await liveFeed.stop();
      if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
      }
      set({
        isActive: false,
        flights: [],
        militaryFlights: [],
        trackedFlights: [],
        uavs: [],
      });
    } catch (error) {
      console.error('[LiveFeed] Failed to stop:', error);
    }
  },
}));
