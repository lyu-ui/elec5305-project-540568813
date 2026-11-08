"""Optional private visual-review sheets (requires ReportLab and Pillow)."""
from pathlib import Path
import json
from PIL import Image
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'outputs/pdf';out.mkdir(parents=True,exist_ok=True)
    target=out/'ELEC5305_Visual_Reference_Review.pdf'
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    c=canvas.Canvas(str(target),pagesize=A4)
    c.setTitle('ELEC5305 - Visual Reference Review')
    W,H=A4
    def text(x,y,value,size=11,color='#182d34'):
        c.setFillColor(color);c.setFont('STSong-Light',size);c.drawString(x,y,value)
    def footer(page):
        text(36,24,'ELEC5305 | 视觉参考核对 | AI 初始标注，尚未人工复核',9,'#536971')
        text(W-70,24,f'{page}/9',9)
    c.setFillColorRGB(.07,.23,.27);c.rect(0,H-170,W,170,fill=1,stroke=0)
    text(38,H-60,'水位视觉参考核对',25,'#ffffff')
    text(38,H-93,'不需要直尺，也不需要重新拍摄',14,'#d4e6e5')
    text(38,H-124,'已有公开视频的 72 个固定时间点 / 8 段录音',11,'#d4e6e5')
    lines=[
      '这份文件用于核对画面中的水面位置，不是最终课程报告。',
      '绿色区域：AI 初步判断的水面可能范围。',
      '蓝色区域：杯口和内底的可能位置。',
      '灰色标记：已排除，不参与相对水位比较。',
      '',
      '目前保留 46 个候选点，排除 26 个点。',
      '第 16、18 段的杯底被画面裁掉，因此整段不做高度归一化。',
      '其它排除原因包括杯底反光、凝露、装饰纹和贴纸遮挡。',
      '',
      '核对时只看水面和杯体，不需要判断模型预测是否正确。',
      '若绿色区域没有覆盖水面，可记录“clip_14，F04，范围偏下”。',
      '若看不清，可记录“无法判断”，不必勉强选出一个位置。',
      '你可以直接回复需要修改的编号；当前文件没有记录你的确认。',
      '',
      '即使完成目视复核，透视、折射和内底厚度仍然带来系统误差。',
      '所以这些标签支持相对趋势与探索性对照，不能证明厘米级精度。',
      '标注范围只是目视估计范围，不是统计置信区间。',
      '',
      '来源：bpiyush/sound-of-water（Hugging Face 公共数据集）。',
      '原视频身份、实际帧时间与排除原因已随实验结果记录。'
    ]
    y=H-210
    for line in lines:
        text(38,y,line,11);y-=24
    footer(1);c.showPage()
    annotations=json.loads((ROOT/'experiments/visual_annotations.json').read_text())['clips']
    frames=pd.read_csv(ROOT/'experiments/results/visual_frame_manifest.csv')
    rois={11:(80,190,180,470),12:(65,335,180,480),13:(85,335,180,480),
          14:(78,265,175,460),15:(65,335,175,480),16:(40,355,155,480),
          17:(55,290,190,480),18:(75,315,195,480)}
    for page,(clip,spec) in enumerate(annotations.items(),2):
        count=sum(v is not None for v in spec['water_y_bounds'])
        text(36,H-40,f'{clip} | 候选 {count}/9 | 人工复核 0/9',18)
        text(36,H-63,'绿色：水面范围   蓝色：杯口与内底范围   EXCLUDED：已排除',10)
        if count==0:
            note='排除原因：杯底在画面外，不能猜测完整杯高。'
        elif clip=='clip_17':
            note='注意：F04、F05 贴纸遮挡；塑料杯内底与泡沫边界较模糊。'
        elif clip=='clip_13':
            note='注意：F01 反光与气泡；F08、F09 装饰纹与水面重叠。'
        elif clip=='clip_15':
            note='注意：锥形玻璃杯、折射与前后水面高度差导致范围较宽。'
        else:
            note='注意：F01 水面无法与杯底或凝露可靠区分，已排除。'
        text(36,H-85,note,10)
        for j in range(9):
            r=frames[(frames['clip']==clip)&(frames.frame==j+1)].iloc[0]
            left,top,right,bottom=rois[int(clip[-2:])]
            raw=Image.open(ROOT/r.image_path).convert('RGB').crop((left,top,right,bottom))
            cell_x=36+(j%3)*177;cell_top=H-108-(j//3)*222
            scale=min(157/(right-left),174/(bottom-top))
            iw,ih=(right-left)*scale,(bottom-top)*scale
            ix=cell_x+(157-iw)/2;iy=cell_top-24-ih
            c.setStrokeColorRGB(.84,.88,.88);c.rect(cell_x-4,cell_top-211,165,207,fill=0,stroke=1)
            text(cell_x,cell_top-17,f'F{j+1:02d} | {r.actual_audio_time_s:.3f} s',10)
            c.drawImage(ImageReader(raw),ix,iy,width=iw,height=ih)
            water=spec['water_y_bounds'][j]
            if water:
                for bounds,color in [(spec['rim_y_bounds'],'#367eae'),(spec['base_y_bounds'],'#367eae'),(water,'#06936c')]:
                    ylo,yhi=bounds
                    c.saveState();c.setFillColor(color);c.setFillAlpha(.22)
                    c.rect(ix,iy+(bottom-yhi)*scale,iw,(yhi-ylo)*scale,fill=1,stroke=0)
                    c.restoreState();c.setStrokeColor(color);c.setLineWidth(.8)
                    for yy in bounds:
                        c.line(ix,iy+(bottom-yy)*scale,ix+iw,iy+(bottom-yy)*scale)
            else:
                c.setFillColorRGB(.25,.28,.29);c.rect(cell_x,cell_top-204,157,15,fill=1,stroke=0)
                text(cell_x+44,cell_top-200,'EXCLUDED',9,'#ffffff')
        text(36,55,'图片仅裁剪以便观察；彩色区域为叠加标记，不改变原始画面内容。',9)
        footer(page);c.showPage()
    c.save();print(target)


if __name__=='__main__':
    main()
