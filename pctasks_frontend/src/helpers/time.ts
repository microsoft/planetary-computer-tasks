import dayjs from "dayjs";
import durationPlugin from "dayjs/plugin/duration";
import relativeTimePlugin from "dayjs/plugin/relativeTime";
import localizedFormatPlugin from "dayjs/plugin/localizedFormat";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import humanizeDuration from "humanize-duration";

import { RunRecord, RunTimesHumanized } from "types/runs";

dayjs.extend(durationPlugin);
dayjs.extend(relativeTimePlugin);
dayjs.extend(localizedFormatPlugin);
dayjs.extend(utc);
dayjs.extend(timezone);

const shortHumanizer = humanizeDuration.humanizer({
  language: "shortEn",
  languages: {
    shortEn: {
      y: () => "y",
      mo: () => "mo",
      w: () => "w",
      d: () => "d",
      h: () => "h",
      m: () => "m",
      s: () => "s",
      ms: () => "ms",
    },
  },
  largest: 2,
  round: true,
  serialComma: false,
  delimiter: " ",
  spacer: "",
  conjunction: "",
});

export const formatRunTimes = (run: RunRecord): RunTimesHumanized => {
  const start = dayjs.utc(run.created);
  const end = dayjs.utc(run.updated);

  const duration = start.diff(end);
  const durationFriendly = isNaN(duration) ? "-" : shortHumanizer(duration);
  return {
    duration,
    durationFriendly,
    startFriendly: start.fromNow(),
    startFormatted: start.tz(dayjs.tz.guess()).format("llll"),
  };
};
