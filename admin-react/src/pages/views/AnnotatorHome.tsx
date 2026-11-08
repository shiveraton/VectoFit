import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { queryKeys } from "../../query";
import client from "../../config/client";
import { bindStyles, each, display, scopeAttributes } from "../../presentation";
import styles from "./AnnotatorHome.module.css";
interface AnnotationDataset {
  id: number;
  name: string;
}
export default function AnnotatorHome(input: {}) {
  const cx = bindStyles(styles);
  const navigate = useNavigate();
  const router = { push: navigate };
  const query = useQuery({
    queryKey: queryKeys.annotationDatasets,
    queryFn: async () => {
      const response = await client.get<AnnotationDataset[]>(
        import.meta.env.MODE === "public"
          ? "/annotator/datasets/"
          : "/datasets/annotation-datasets/",
      );
      const data: unknown = response.data;
      if (
        !Array.isArray(data) ||
        !data.every(
          (item) =>
            item &&
            typeof item === "object" &&
            Number.isInteger(item.id) &&
            item.id > 0 &&
            typeof item.name === "string",
        )
      ) {
        throw new Error("Invalid annotation dataset response.");
      }
      return data as AnnotationDataset[];
    },
  });
  const datasets = query.data ?? [];
  const error = query.error ? "Unable to load annotation datasets." : null;
  const isLoading = query.isFetching;
  const fetchDatasets = () => query.refetch();
  const openDataset = (id: number) => router.push("/annotator/" + id);
  return (
    <>
      <div
        {...scopeAttributes(input)}
        data-v-annotator-home=""
        className={cx("annotator-page")}
      >
        <header data-v-annotator-home="" className={cx("page-header")}>
          <div data-v-annotator-home="" className={cx("page-heading")}>
            <div data-v-annotator-home="" className={cx("eyebrow")}>
              <span
                data-v-annotator-home=""
                className={cx("eyebrow-dot")}
              ></span>
              {" DATASET ANNOTATION "}
            </div>
            <h1 data-v-annotator-home="">{"Choose a Dataset"}</h1>
            <p data-v-annotator-home="">
              {
                " Select a shared dataset to review and annotate its eligible samples. "
              }
            </p>
          </div>
          <button
            data-v-annotator-home=""
            disabled={isLoading}
            onClick={() => fetchDatasets()}
            className={cx("secondary-button")}
          >
            <span data-v-annotator-home="" className={cx("button-icon")}>
              {"↻"}
            </span>
            {" Refresh "}
          </button>
        </header>
        <section data-v-annotator-home="" className={cx("content-card")}>
          <div data-v-annotator-home="" className={cx("section-header")}>
            <div data-v-annotator-home="" className={cx("section-title-row")}>
              <div
                data-v-annotator-home=""
                className={cx("section-marker")}
              ></div>
              <div data-v-annotator-home="">
                <h2 data-v-annotator-home="">{"Available Datasets"}</h2>
              </div>
            </div>
            <span data-v-annotator-home="" className={cx("status-badge")}>
              {display(datasets.length)}
              {" DATASETS "}
            </span>
          </div>
          <div data-v-annotator-home="" className={cx("dataset-list")}>
            {isLoading ? (
              <div data-v-annotator-home="" className={cx("empty-state")}>
                <div
                  data-v-annotator-home=""
                  className={cx("loading-spinner")}
                ></div>
                <p data-v-annotator-home="">
                  {"Loading annotation datasets..."}
                </p>
              </div>
            ) : error ? (
              <div
                data-v-annotator-home=""
                className={cx("empty-state error-state")}
              >
                <h3 data-v-annotator-home="">{"Unable to Load Datasets"}</h3>
                <p data-v-annotator-home="">{display(error)}</p>
                <button
                  data-v-annotator-home=""
                  onClick={() => fetchDatasets()}
                  className={cx("secondary-button")}
                >
                  {" Try Again "}
                </button>
              </div>
            ) : datasets.length === 0 ? (
              <div data-v-annotator-home="" className={cx("empty-state")}>
                <h3 data-v-annotator-home="">{"No Annotation Datasets"}</h3>
                <p data-v-annotator-home="">
                  {
                    " There are currently no shared datasets available for annotation. Please check again later. "
                  }
                </p>
              </div>
            ) : (
              <div data-v-annotator-home="" className={cx("dataset-grid")}>
                {each(datasets).map(([_index, dataset]) => (
                  <button
                    data-v-annotator-home=""
                    key={dataset.id}
                    type="button"
                    onClick={() => {
                      openDataset(dataset.id);
                    }}
                    className={cx("dataset-card")}
                  >
                    <div
                      data-v-annotator-home=""
                      className={cx("dataset-info")}
                    >
                      <span
                        data-v-annotator-home=""
                        className={cx("dataset-label")}
                      >
                        {" DATASET #"}
                        {display(dataset.id)}
                      </span>
                      <h3 data-v-annotator-home="">{display(dataset.name)}</h3>
                      <p data-v-annotator-home="">
                        {"Open dataset for annotation"}
                      </p>
                    </div>
                    <span
                      data-v-annotator-home=""
                      className={cx("dataset-arrow")}
                    >
                      {"→"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {!isLoading && !error && datasets.length > 0 ? (
            <div data-v-annotator-home="" className={cx("card-footer")}>
              {" Showing "}
              {display(datasets.length)}
              {" available annotation "}
              {display(datasets.length === 1 ? "dataset" : "datasets")}
              {". "}
            </div>
          ) : null}
        </section>
      </div>
    </>
  );
}
