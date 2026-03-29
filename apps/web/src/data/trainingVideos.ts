export interface TrainingVideoItem {
  id: string;
  src: string;
  titleKey: string;
  descriptionKey: string;
}

export const TRAINING_VIDEO_PLAYLIST: TrainingVideoItem[] = [
  {
    id: "1",
    src: "/videos/01-import-reports.mp4",
    titleKey: "learning.videoImport.title",
    descriptionKey: "learning.videoImport.desc",
  },
  {
    id: "2",
    src: "/videos/02-summary-tab.mp4",
    titleKey: "learning.videoSummary.title",
    descriptionKey: "learning.videoSummary.desc",
  },
  {
    id: "3",
    src: "/videos/03-go.mp4",
    titleKey: "learning.videoGo.title",
    descriptionKey: "learning.videoGo.desc",
  },
];
