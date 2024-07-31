import React, { useMemo, useState } from 'react';
import { PanelProps, DashboardCursorSync } from '@grafana/data';
import { EventBusPlugin, TooltipDisplayMode, TooltipPlugin2, usePanelContext, useTheme2 } from '@grafana/ui';
import { TimeRange2, TooltipHoverMode } from '@grafana/ui/src/components/uPlot/plugins/TooltipPlugin2';
import { TimelineChart } from 'app/core/components/TimelineChart/TimelineChart';
import {
  prepareTimelineFields,
  prepareTimelineLegendItems,
  TimelineMode,
} from 'app/core/components/TimelineChart/utils';
import { AnnotationsPlugin2 } from '../timeseries/plugins/AnnotationsPlugin2';
import { OutsideRangePlugin } from '../timeseries/plugins/OutsideRangePlugin';
import { getTimezones } from '../timeseries/utils';
import { StateTimelineTooltip2 } from './StateTimelineTooltip2';
import { Options } from './panelcfg.gen';

interface MyTimelinePanelProps extends PanelProps<Options> {}

const MyTimelinePanel = ({
                           data,
                           timeRange,
                           timeZone,
                           options,
                           width,
                           height,
                           replaceVariables,
                           onChangeTimeRange,
                         }: MyTimelinePanelProps) => {
  const theme = useTheme2();

  const [newAnnotationRange, setNewAnnotationRange] = useState<TimeRange2 | null>(null);
  const { sync, eventsScope, canAddAnnotations, dataLinkPostProcessor, eventBus } = usePanelContext();
  const cursorSync = sync?.() ?? DashboardCursorSync.Off;

  const { frames, warn } = useMemo(
      () => prepareTimelineFields(data.series, options.mergeValues ?? true, timeRange, theme),
      [data.series, options.mergeValues, timeRange, theme]
  );

  const legendItems = useMemo(
      () => prepareTimelineLegendItems(frames, options.legend, theme),
      [frames, options.legend, theme]
  );

  const timezones = useMemo(() => getTimezones(options.timezone, timeZone), [options.timezone, timeZone]);

  if (!frames || warn) {
    return (
        <div className="panel-empty">
          <p>{warn ?? 'No data found in response'}</p>
        </div>
    );
  }

  const enableAnnotationCreation = Boolean(canAddAnnotations && canAddAnnotations());

  return (
      <TimelineChart
          theme={theme}
          frames={frames}
          structureRev={data.structureRev}
          timeRange={timeRange}
          timeZone={timezones}
          width={width}
          height={height}
          legendItems={legendItems}
          {...options}
          mode={TimelineMode.Changes}
          replaceVariables={replaceVariables}
          dataLinkPostProcessor={dataLinkPostProcessor}
          cursorSync={cursorSync}
      >
        {(builder, alignedFrame) => {
          return (
              <>
                {cursorSync !== DashboardCursorSync.Off && (
                    <EventBusPlugin config={builder} eventBus={eventBus} frame={alignedFrame} />
                )}
                {options.tooltip.mode !== TooltipDisplayMode.None && (
                    <TooltipPlugin2
                        config={builder}
                        hoverMode={
                          options.tooltip.mode === TooltipDisplayMode.Multi ? TooltipHoverMode.xAll : TooltipHoverMode.xOne
                        }
                        queryZoom={onChangeTimeRange}
                        syncMode={cursorSync}
                        syncScope={eventsScope}
                        render={(u, dataIdxs, seriesIdx, isPinned, dismiss, timeRange2, viaSync) => {
                          if (enableAnnotationCreation && timeRange2 != null) {
                            setNewAnnotationRange(timeRange2);
                            dismiss();
                            return;
                          }

                          const annotate = () => {
                            let xVal = u.posToVal(u.cursor.left!, 'x');

                            setNewAnnotationRange({ from: xVal, to: xVal });
                            dismiss();
                          };

                          return (
                              <StateTimelineTooltip2
                                  series={alignedFrame}
                                  dataIdxs={dataIdxs}
                                  seriesIdx={seriesIdx}
                                  mode={viaSync ? TooltipDisplayMode.Multi : options.tooltip.mode}
                                  sortOrder={options.tooltip.sort}
                                  isPinned={isPinned}
                                  timeRange={timeRange}
                                  annotate={enableAnnotationCreation ? annotate : undefined}
                                  withDuration={true}
                                  maxHeight={options.tooltip.maxHeight}
                                  setNewTimeRange={onChangeTimeRange} // Pass the function to change time range
                              />
                          );
                        }}
                        maxWidth={options.tooltip.maxWidth}
                    />
                )}
                <AnnotationsPlugin2
                    annotations={data.annotations ?? []}
                    config={builder}
                    timeZone={timeZone}
                    newRange={newAnnotationRange}
                    setNewRange={setNewAnnotationRange}
                    canvasRegionRendering={false}
                />
                <OutsideRangePlugin config={builder} onChangeTimeRange={onChangeTimeRange} />
              </>
          );
        }}
      </TimelineChart>
  );
};

export default MyTimelinePanel;
