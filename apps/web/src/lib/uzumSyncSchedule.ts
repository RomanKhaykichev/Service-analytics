/** Next scheduled Uzum API sync (06:00 and 18:00 Asia/Tashkent). */

const UZ_TZ = "Asia/Tashkent";
const SYNC_HOURS = [6, 18] as const;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function getUzParts(date: Date) {
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: UZ_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(fmt.formatToParts(date).map((p) => [p.type, p.value]));
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute),
  };
}

function uzInstant(year: number, month: number, day: number, hour: number, minute: number): Date {
  return new Date(`${year}-${pad2(month)}-${pad2(day)}T${pad2(hour)}:${pad2(minute)}:00+05:00`);
}

function addDaysInUz(year: number, month: number, day: number, days: number) {
  const noon = uzInstant(year, month, day, 12, 0);
  noon.setTime(noon.getTime() + days * 86_400_000);
  return getUzParts(noon);
}

export function getNextUzumSyncSchedule(now: Date = new Date()): {
  dateLabel: string;
  timeLabel: string;
} {
  const { year, month, day } = getUzParts(now);

  for (let dayOffset = 0; dayOffset < 2; dayOffset += 1) {
    const parts =
      dayOffset === 0 ? { year, month, day } : addDaysInUz(year, month, day, dayOffset);

    for (const hour of SYNC_HOURS) {
      const candidate = uzInstant(parts.year, parts.month, parts.day, hour, 0);
      if (candidate.getTime() > now.getTime()) {
        return {
          dateLabel: `${pad2(parts.day)}.${pad2(parts.month)}`,
          timeLabel: `${pad2(hour)}:00`,
        };
      }
    }
  }

  const tomorrow = addDaysInUz(year, month, day, 1);
  return {
    dateLabel: `${pad2(tomorrow.day)}.${pad2(tomorrow.month)}`,
    timeLabel: "06:00",
  };
}
