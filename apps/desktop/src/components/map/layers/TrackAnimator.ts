/**
 * Track animation controller for flight/vessel track playback.
 */
export class TrackAnimator {
  private _currentTime = 0;
  private _maxTime = 100;
  private _speed = 1.0;
  private _playing = false;
  private _rafId: number | null = null;
  private _lastFrameTime = 0;
  private _onUpdate: (time: number) => void;

  constructor(onUpdate: (time: number) => void, maxTime = 100) {
    this._onUpdate = onUpdate;
    this._maxTime = maxTime;
  }

  get currentTime() {
    return this._currentTime;
  }

  get maxTime() {
    return this._maxTime;
  }

  get playing() {
    return this._playing;
  }

  get speed() {
    return this._speed;
  }

  setMaxTime(t: number) {
    this._maxTime = t;
  }

  setSpeed(s: number) {
    this._speed = Math.max(0.5, Math.min(s, 10));
  }

  seek(time: number) {
    this._currentTime = Math.max(0, Math.min(time, this._maxTime));
    this._onUpdate(this._currentTime);
  }

  play() {
    if (this._playing) return;
    this._playing = true;
    this._lastFrameTime = performance.now();
    this._tick();
  }

  pause() {
    this._playing = false;
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  toggle() {
    if (this._playing) this.pause();
    else this.play();
  }

  reset() {
    this.pause();
    this._currentTime = 0;
    this._onUpdate(0);
  }

  destroy() {
    this.pause();
  }

  private _tick = () => {
    if (!this._playing) return;

    const now = performance.now();
    const delta = (now - this._lastFrameTime) / 1000; // seconds
    this._lastFrameTime = now;

    this._currentTime += delta * this._speed;

    if (this._currentTime >= this._maxTime) {
      this._currentTime = 0; // Loop
    }

    this._onUpdate(this._currentTime);
    this._rafId = requestAnimationFrame(this._tick);
  };
}
