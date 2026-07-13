export interface OptionData {
  strikePrice: number;
  expiryDate: string;
  underlying: string;
  identifier: string;
  openInterest: number;
  changeinOpenInterest: number;
  totalTradedVolume: number;
  impliedVolatility: number;
  lastPrice: number;
  underlyingValue: number;
}

export interface StrikeRecord {
  strikePrice: number;
  expiryDate: string;
  CE?: OptionData;
  PE?: OptionData;
}

export interface OptionChainData {
  source: "live" | "mock";
  records: {
    expiryDates: string[];
    underlyingValue: number;
    timestamp: string;
    data: StrikeRecord[];
  };
  filtered?: {
    data: StrikeRecord[];
  };
}

export interface OptionChainResponse {
  data: OptionChainData;
  fetched_at: string;
  source: "live-polled" | "mock";
  age_minutes: number;
}

// Generate realistic option chain data for NIFTY spot = 24248.50
const spot = 24248.50;
const expiry = "2026-07-16";
const underlying = "NIFTY";

const rawStrikes = [
  23850, 23900, 23950, 24000, 24050, 24100, 24150, 24200, 24250,
  24300, 24350, 24400, 24450, 24500, 24550, 24600, 24650
];

// Helper to calculate CE price based on intrinsic + extrinsic
const getCEPrice = (strike: number): number => {
  const intrinsic = Math.max(spot - strike, 0);
  // Extrinsic value decays away from spot
  const distance = Math.abs(strike - spot);
  const extrinsic = Math.max(150 - distance * 0.5, 3.5);
  return Number((intrinsic + extrinsic).toFixed(2));
};

// Helper to calculate PE price based on intrinsic + extrinsic
const getPEPrice = (strike: number): number => {
  const intrinsic = Math.max(strike - spot, 0);
  const distance = Math.abs(strike - spot);
  const extrinsic = Math.max(150 - distance * 0.5, 3.5);
  return Number((intrinsic + extrinsic).toFixed(2));
};

// Helper to get realistic open interest (high near round numbers)
const getOI = (strike: number, isCall: boolean): number => {
  const distance = Math.abs(strike - spot);
  // Base OI drops as we go further OTM or deep ITM
  let base = Math.max(80000 - distance * 150, 2000);
  
  // Round number multiplier (e.g. 24000, 24500, 24200)
  if (strike % 500 === 0) {
    base *= 2.5;
  } else if (strike % 100 === 0) {
    base *= 1.5;
  }

  // Calls have higher OI at higher strikes, Puts at lower strikes
  if (isCall && strike > spot) {
    base *= 1.3;
  } else if (!isCall && strike < spot) {
    base *= 1.3;
  }

  return Math.round(base);
};

// Helper to get realistic IV (smile shape: higher for OTM options)
const getIV = (strike: number): number => {
  const distancePercent = Math.abs(strike - spot) / spot;
  // Smile shape: minimum around ATM, increasing on both sides
  const iv = 11.2 + (distancePercent * 100) * 1.5;
  return Number(iv.toFixed(2));
};

// Generate data list
const strikesData: StrikeRecord[] = rawStrikes.map((strike) => {
  const ceOI = getOI(strike, true);
  const peOI = getOI(strike, false);
  
  const ceChangeOI = Math.round(ceOI * (Math.random() * 0.2 - 0.05));
  const peChangeOI = Math.round(peOI * (Math.random() * 0.25 - 0.05));

  const ceVol = Math.round(ceOI * (1.5 + Math.random()));
  const peVol = Math.round(peOI * (1.5 + Math.random()));

  return {
    strikePrice: strike,
    expiryDate: expiry,
    CE: {
      strikePrice: strike,
      expiryDate: expiry,
      underlying,
      identifier: `OPT${underlying}16-07-2026CE${strike}`,
      openInterest: ceOI,
      changeinOpenInterest: ceChangeOI,
      totalTradedVolume: ceVol,
      impliedVolatility: getIV(strike),
      lastPrice: getCEPrice(strike),
      underlyingValue: spot,
    },
    PE: {
      strikePrice: strike,
      expiryDate: expiry,
      underlying,
      identifier: `OPT${underlying}16-07-2026PE${strike}`,
      openInterest: peOI,
      changeinOpenInterest: peChangeOI,
      totalTradedVolume: peVol,
      impliedVolatility: getIV(strike),
      lastPrice: getPEPrice(strike),
      underlyingValue: spot,
    }
  };
});

export const mockOptionChainResponse: OptionChainResponse = {
  data: {
    source: "live",
    records: {
      expiryDates: [expiry, "2026-07-23", "2026-07-30"],
      underlyingValue: spot,
      timestamp: "14-Jul-2026 15:30:00",
      data: strikesData,
    },
    filtered: {
      data: strikesData,
    }
  },
  fetched_at: "2026-07-14T10:00:00.000000+00:00",
  source: "live-polled",
  age_minutes: 4.5,
};
