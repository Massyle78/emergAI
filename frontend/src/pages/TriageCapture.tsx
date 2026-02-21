import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AudioVisualizer } from "@/components/capture/AudioVisualizer";
import { RecordingControls } from "@/components/capture/RecordingControls";
import {
  StepIndicator,
  type CaptureStep,
} from "@/components/capture/StepIndicator";
import { UploadProgress } from "@/components/capture/UploadProgress";
import { WebcamPreview } from "@/components/capture/WebcamPreview";
import { useMediaRecorder } from "@/hooks/useMediaRecorder";
import { useMediaStream } from "@/hooks/useMediaStream";
import { useUpload } from "@/hooks/useUpload";

const VIDEO_MAX_SECONDS = 30;
const AUDIO_MAX_SECONDS = 60;

const VIDEO_CONSTRAINTS: MediaStreamConstraints = {
  video: { facingMode: "user", width: 640, height: 480 },
  audio: false,
};

const AUDIO_CONSTRAINTS: MediaStreamConstraints = {
  video: false,
  audio: { echoCancellation: true, noiseSuppression: true },
};

/**
 * Multi-step triage capture flow:
 *  1. Permissions – request camera & mic access
 *  2. Video – 30 s face recording for rPPG vitals
 *  3. Audio – 60 s symptom description
 *  4. Review – preview recordings before submission
 */
export function TriageCapture() {
  const [step, setStep] = useState<CaptureStep>("permissions");

  const videoStream = useMediaStream(VIDEO_CONSTRAINTS);
  const audioStream = useMediaStream(AUDIO_CONSTRAINTS);

  const videoRec = useMediaRecorder(videoStream.stream, "video/webm");
  const audioRec = useMediaRecorder(audioStream.stream, "audio/webm");
  const upload = useUpload();

  const goNext = useCallback(
    (next: CaptureStep) => setStep(next),
    [],
  );

  return (
    <div className="flex flex-1 flex-col items-center gap-6 p-6">
      <StepIndicator current={step} />

      <div className="w-full max-w-2xl">
        {step === "permissions" && (
          <PermissionsStep
            videoStream={videoStream}
            audioStream={audioStream}
            onReady={() => goNext("video")}
          />
        )}
        {step === "video" && (
          <VideoStep
            stream={videoStream.stream}
            recorder={videoRec}
            onDone={() => goNext("audio")}
          />
        )}
        {step === "audio" && (
          <AudioStep
            stream={audioStream.stream}
            recorder={audioRec}
            onDone={() => goNext("review")}
          />
        )}
        {step === "review" && (
          <ReviewStep
            videoBlob={videoRec.blob}
            audioBlob={audioRec.blob}
            upload={upload}
            onRestart={() => {
              videoRec.reset();
              audioRec.reset();
              upload.reset();
              setStep("video");
            }}
          />
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 1: Permissions                                                */
/* ------------------------------------------------------------------ */
interface PermissionsStepProps {
  videoStream: ReturnType<typeof useMediaStream>;
  audioStream: ReturnType<typeof useMediaStream>;
  onReady: () => void;
}

function PermissionsStep({
  videoStream,
  audioStream,
  onReady,
}: PermissionsStepProps) {
  const cameraOk = videoStream.status === "active";
  const micOk = audioStream.status === "active";
  const allOk = cameraOk && micOk;

  return (
    <div className="kiosk-card text-center">
      <h2 className="text-2xl font-bold text-slate-900">
        Set Up Your Devices
      </h2>
      <p className="mt-2 text-slate-500">
        We need access to your camera and microphone to perform the triage
        assessment. Your data is processed securely and never stored
        permanently.
      </p>

      <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:justify-center">
        <PermissionButton
          label="Camera"
          granted={cameraOk}
          denied={videoStream.status === "denied"}
          loading={videoStream.status === "requesting"}
          error={videoStream.error}
          onClick={() => void videoStream.request()}
        />
        <PermissionButton
          label="Microphone"
          granted={micOk}
          denied={audioStream.status === "denied"}
          loading={audioStream.status === "requesting"}
          error={audioStream.error}
          onClick={() => void audioStream.request()}
        />
      </div>

      {allOk && (
        <button onClick={onReady} className="kiosk-btn-primary mt-8">
          Continue
        </button>
      )}
    </div>
  );
}

interface PermissionButtonProps {
  label: string;
  granted: boolean;
  denied: boolean;
  loading: boolean;
  error: string | null;
  onClick: () => void;
}

function PermissionButton({
  label,
  granted,
  denied,
  loading,
  error,
  onClick,
}: PermissionButtonProps) {
  if (granted) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-accent-50 px-5 py-3 text-accent-700 ring-1 ring-accent-200">
        <CheckCircle />
        {label} ready
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={onClick}
        disabled={loading}
        className="kiosk-btn-secondary"
      >
        {loading ? "Requesting..." : `Enable ${label}`}
      </button>
      {denied && error && (
        <p className="text-xs text-danger-600">
          Access denied. Please allow {label.toLowerCase()} in your browser
          settings.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 2: Video recording                                            */
/* ------------------------------------------------------------------ */
interface VideoStepProps {
  stream: MediaStream | null;
  recorder: ReturnType<typeof useMediaRecorder>;
  onDone: () => void;
}

function VideoStep({ stream, recorder, onDone }: VideoStepProps) {
  useAutoStop(recorder, VIDEO_MAX_SECONDS);

  const done = recorder.status === "stopped";

  return (
    <div className="kiosk-card space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">
          Record Your Face
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Look directly at the camera for {VIDEO_MAX_SECONDS} seconds. Stay
          still — we&apos;ll measure your heart rate from the video.
        </p>
      </div>

      <WebcamPreview stream={stream} />

      {!done ? (
        <RecordingControls
          recording={recorder.status === "recording"}
          elapsed={recorder.elapsed}
          onStart={recorder.start}
          onStop={recorder.stop}
          label="Start Video Recording"
          maxSeconds={VIDEO_MAX_SECONDS}
        />
      ) : (
        <div className="flex flex-col items-center gap-4">
          <p className="font-medium text-accent-600">
            Video recorded successfully
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => {
                recorder.reset();
              }}
              className="kiosk-btn-secondary"
            >
              Re-record
            </button>
            <button onClick={onDone} className="kiosk-btn-primary">
              Continue to Audio
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 3: Audio recording                                            */
/* ------------------------------------------------------------------ */
interface AudioStepProps {
  stream: MediaStream | null;
  recorder: ReturnType<typeof useMediaRecorder>;
  onDone: () => void;
}

function AudioStep({ stream, recorder, onDone }: AudioStepProps) {
  useAutoStop(recorder, AUDIO_MAX_SECONDS);

  const isRecording = recorder.status === "recording";
  const done = recorder.status === "stopped";

  return (
    <div className="kiosk-card space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">
          Describe Your Symptoms
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Speak clearly and describe what brought you to the emergency
          department today. Include when symptoms started and their severity.
        </p>
      </div>

      <AudioVisualizer stream={stream} active={isRecording} />

      {!done ? (
        <RecordingControls
          recording={isRecording}
          elapsed={recorder.elapsed}
          onStart={recorder.start}
          onStop={recorder.stop}
          label="Start Audio Recording"
          maxSeconds={AUDIO_MAX_SECONDS}
        />
      ) : (
        <div className="flex flex-col items-center gap-4">
          <p className="font-medium text-accent-600">
            Audio recorded successfully
          </p>
          <div className="flex gap-3">
            <button onClick={() => recorder.reset()} className="kiosk-btn-secondary">
              Re-record
            </button>
            <button onClick={onDone} className="kiosk-btn-primary">
              Review & Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 4: Review & Submit                                            */
/* ------------------------------------------------------------------ */
interface ReviewStepProps {
  videoBlob: Blob | null;
  audioBlob: Blob | null;
  upload: ReturnType<typeof useUpload>;
  onRestart: () => void;
}

function ReviewStep({ videoBlob, audioBlob, upload, onRestart }: ReviewStepProps) {
  const navigate = useNavigate();
  const submitting = upload.phase !== "idle";

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!videoBlob) return;
    const url = URL.createObjectURL(videoBlob);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [videoBlob]);

  useEffect(() => {
    if (!audioBlob) return;
    const url = URL.createObjectURL(audioBlob);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audioBlob]);

  const handleSubmit = useCallback(() => {
    if (videoBlob && audioBlob) {
      void upload.submit(videoBlob, audioBlob);
    }
  }, [videoBlob, audioBlob, upload]);

  if (submitting) {
    return (
      <UploadProgress
        phase={upload.phase}
        progress={upload.progress}
        error={upload.error}
        processingStatus={upload.processingStatus}
        onRetry={() => void upload.retry()}
        onDone={() => navigate("/")}
      />
    );
  }

  return (
    <div className="kiosk-card space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">
          Review Your Recordings
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Preview your video and audio before submitting for analysis.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Video</h3>
          {videoUrl ? (
            <video
              src={videoUrl}
              controls
              className="w-full rounded-lg bg-slate-900"
            />
          ) : (
            <p className="text-sm text-slate-400">No video recorded</p>
          )}
          {videoBlob && (
            <p className="mt-1 text-xs text-slate-400">
              {formatSize(videoBlob.size)}
            </p>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Audio</h3>
          {audioUrl ? (
            <audio src={audioUrl} controls className="w-full" />
          ) : (
            <p className="text-sm text-slate-400">No audio recorded</p>
          )}
          {audioBlob && (
            <p className="mt-1 text-xs text-slate-400">
              {formatSize(audioBlob.size)}
            </p>
          )}
        </div>
      </div>

      <div className="flex justify-center gap-3">
        <button onClick={onRestart} className="kiosk-btn-secondary">
          Start Over
        </button>
        <button
          onClick={handleSubmit}
          disabled={!videoBlob || !audioBlob}
          className="kiosk-btn-primary"
        >
          Submit for Analysis
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared helpers                                                     */
/* ------------------------------------------------------------------ */
function useAutoStop(
  recorder: ReturnType<typeof useMediaRecorder>,
  maxSeconds: number,
) {
  useEffect(() => {
    if (recorder.status === "recording" && recorder.elapsed >= maxSeconds) {
      recorder.stop();
    }
  }, [recorder, maxSeconds]);
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CheckCircle() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
