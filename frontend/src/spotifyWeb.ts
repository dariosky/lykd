import { apiService } from "./api";

let sdkLoading: Promise<void> | null = null;
let deviceReady: Promise<string> | null = null;
let cachedDeviceId: string | null = null;

function loadSdk(): Promise<void> {
  if (sdkLoading) return sdkLoading;
  sdkLoading = new Promise<void>((resolve, reject) => {
    if ((window as any).Spotify) return resolve();
    const script = document.createElement("script");
    script.src = "https://sdk.scdn.co/spotify-player.js";
    script.async = true;
    (window as any).onSpotifyWebPlaybackSDKReady = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Spotify SDK"));
    document.head.appendChild(script);
  });
  return sdkLoading;
}

export async function ensureWebPlaybackDevice(): Promise<string> {
  if (cachedDeviceId) return cachedDeviceId;
  if (deviceReady) return deviceReady;

  deviceReady = new Promise<string>((resolve, reject) => {
    (async () => {
      try {
        await loadSdk();
        const Spotify = (window as any).Spotify;
        if (!Spotify || !Spotify.Player) {
          reject(new Error("SDK unavailable"));
          return;
        }

        const player = new Spotify.Player({
          name: "LYKD",
          getOAuthToken: async (cb: (token: string) => void) => {
            try {
              const { access_token } = await apiService.getSpotifyToken();
              cb(access_token);
            } catch (e) {
              // No token, cannot proceed
            }
          },
          volume: 0.8,
        });

        player.addListener("ready", ({ device_id }: any) => {
          cachedDeviceId = device_id;
          resolve(device_id);
        });
        player.addListener("not_ready", ({ device_id }: any) => {
          if (cachedDeviceId === device_id) cachedDeviceId = null;
        });
        player.addListener("initialization_error", ({ message }: any) =>
          reject(new Error(message)),
        );
        player.addListener("authentication_error", ({ message }: any) =>
          reject(new Error(message)),
        );
        player.addListener("account_error", ({ message }: any) =>
          reject(new Error(message)),
        );

        const ok = await player.connect();
        if (!ok) reject(new Error("Failed to connect player"));
      } catch (e) {
        reject(e as Error);
      }
    })();
  });

  return deviceReady;
}
