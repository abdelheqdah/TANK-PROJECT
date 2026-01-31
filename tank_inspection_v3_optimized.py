"""
Tank Bottom Inspection System v3.0 - Optimized
تتبع فحص قاع الخزان - نسخة محسّنة
"""

print("Loading Tank Inspection System v3.0...")
print("=" * 60)

import json
import os
from datetime import datetime

print("✓ Basic modules loaded")

import numpy as np
print("✓ NumPy loaded")

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for speed
import matplotlib.pyplot as plt
print("✓ Matplotlib loaded")

print("=" * 60)
print()

class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON"""
    def default(self, obj):
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, np.int_)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float_)):
            return float(obj)
        return super().default(obj)

class TankBottomInspection:
    """Tank Bottom Inspection with Length-Based Tracking"""
    
    def __init__(self, progress_file='inspection_progress.json'):
        print("Initializing inspection system...")
        
        self.progress_file = progress_file
        
        # Tank specifications
        self.diameter = 55.25
        self.radius = self.diameter / 2
        self.annular_width = 0.6
        self.annular_plates = 20
        self.annular_angle = 360 / self.annular_plates
        self.plate_width = 2.39
        
        # Row configuration
        self.row_config = {
            1: 11, 2: 4, 3: 5, 4: 6, 5: 6, 6: 6, 7: 7, 8: 6, 9: 7, 10: 6, 11: 7,
            12: 6, 13: 7, 14: 6, 15: 7, 16: 6, 17: 6, 18: 6, 19: 5, 20: 4, 21: 11
        }
        
        self.inner_radius = self.radius - self.annular_width
        
        print("  Calculating weld geometry...")
        self.welds = self._initialize_welds()
        
        print("  Loading saved progress...")
        self.load_progress()
        
        total = self.get_total_welds()
        print(f"✓ System ready! {total} welds tracked")
        print()
    
    def _initialize_welds(self):
        """Initialize all welds with length tracking"""
        welds = {'horizontal': [], 'vertical': [], 'annular': []}
        
        y_start = 10.5 * self.plate_width
        fixed_x = [-10.8, -8.4, -6.0, -3.6, -1.2, 1.2, 3.6, 6.0, 8.4, 10.8]
        
        # Horizontal welds
        for row_idx in range(20):
            y_lo = y_start - ((row_idx + 1) * self.plate_width)
            if abs(y_lo) <= self.inner_radius:
                x_h = np.sqrt(max(0, self.inner_radius**2 - y_lo**2))
                welds['horizontal'].append({
                    'id': f'H{row_idx + 1}',
                    'row': row_idx + 1,
                    'y': y_lo,
                    'x_start': -x_h,
                    'x_end': x_h,
                    'total_length': 2 * x_h,
                    'inspected_length': 0.0,
                    'inspected': False
                })
        
        # Vertical welds (simplified for speed)
        for row_idx in range(21):
            row_num = row_idx + 1
            num_vertical = self.row_config[row_num] - 1
            
            y_hi = y_start - (row_idx * self.plate_width)
            y_lo = y_hi - self.plate_width
            
            if row_idx == 0:  # Row 1
                for i, vx in enumerate(fixed_x):
                    y_top = np.sqrt(max(0, self.inner_radius**2 - vx**2))
                    welds['vertical'].append({
                        'id': f'V{row_num}_{i+1}',
                        'row': row_num,
                        'x': vx,
                        'y_start': y_lo,
                        'y_end': y_top,
                        'total_length': y_top - y_lo,
                        'inspected_length': 0.0,
                        'inspected': False
                    })
            elif row_idx == 20:  # Row 21
                for i, vx in enumerate(fixed_x):
                    y_bot = -np.sqrt(max(0, self.inner_radius**2 - vx**2))
                    welds['vertical'].append({
                        'id': f'V{row_num}_{i+1}',
                        'row': row_num,
                        'x': vx,
                        'y_start': y_hi,
                        'y_end': y_bot,
                        'total_length': y_hi - y_bot,
                        'inspected_length': 0.0,
                        'inspected': False
                    })
            else:  # Interior rows
                y_mid = (y_hi + y_lo) / 2
                x_lim = np.sqrt(max(0, self.inner_radius**2 - y_mid**2))
                v_x = np.linspace(-x_lim * 0.9, x_lim * 0.9, num_vertical)
                
                for v_idx, vx in enumerate(v_x):
                    welds['vertical'].append({
                        'id': f'V{row_num}_{v_idx + 1}',
                        'row': row_num,
                        'x': float(vx),
                        'y_start': y_lo,
                        'y_end': y_hi,
                        'total_length': self.plate_width,
                        'inspected_length': 0.0,
                        'inspected': False
                    })
        
        # Annular welds
        segment_length = (2 * np.pi * self.inner_radius) / self.annular_plates
        for i in range(self.annular_plates):
            welds['annular'].append({
                'id': f'AR{i+1}',
                'plate': i + 1,
                'type': 'radial_short',
                'total_length': self.annular_width,
                'inspected_length': 0.0,
                'angle': i * self.annular_angle,
                'inspected': False
            })
            
            welds['annular'].append({
                'id': f'AC{i+1}',
                'plate': i + 1,
                'type': 'circumferential_segment',
                'angle_start': i * self.annular_angle,
                'angle_end': (i + 1) * self.annular_angle,
                'total_length': segment_length,
                'inspected_length': 0.0,
                'radius': self.inner_radius,
                'inspected': False
            })
        
        return welds
    
    def set_weld_length(self, weld_id, inspected_meters):
        """Set inspected length for a weld"""
        weld = self._find_weld(weld_id)
        if weld:
            weld['inspected_length'] = min(inspected_meters, weld['total_length'])
            weld['inspected'] = (weld['inspected_length'] >= weld['total_length'])
            self.save_progress()
            return True
        return False
    
    def add_weld_length(self, weld_id, additional_meters):
        """Add incremental length"""
        weld = self._find_weld(weld_id)
        if weld:
            new_length = min(weld['inspected_length'] + additional_meters, weld['total_length'])
            weld['inspected_length'] = new_length
            weld['inspected'] = (new_length >= weld['total_length'])
            self.save_progress()
            return True
        return False
    
    def mark_weld_complete(self, weld_id):
        """Mark weld as completely inspected"""
        weld = self._find_weld(weld_id)
        if weld:
            weld['inspected_length'] = weld['total_length']
            weld['inspected'] = True
            self.save_progress()
            return True
        return False
    
    def update_weld_lengths(self, updates_dict):
        """Batch update multiple welds"""
        for weld_id, meters in updates_dict.items():
            self.set_weld_length(weld_id, meters)
    
    def _find_weld(self, weld_id):
        """Find weld by ID"""
        for weld_type in ['horizontal', 'vertical', 'annular']:
            for weld in self.welds[weld_type]:
                if weld['id'] == weld_id:
                    return weld
        return None
    
    def get_length_statistics(self):
        """Get comprehensive length-based statistics"""
        stats = {
            'horizontal': {'total': 0, 'inspected': 0, 'percentage': 0},
            'vertical': {'total': 0, 'inspected': 0, 'percentage': 0},
            'annular': {'total': 0, 'inspected': 0, 'percentage': 0},
            'overall': {'total': 0, 'inspected': 0, 'percentage': 0}
        }
        
        for weld_type in ['horizontal', 'vertical', 'annular']:
            for weld in self.welds[weld_type]:
                stats[weld_type]['total'] += weld['total_length']
                stats[weld_type]['inspected'] += weld['inspected_length']
                stats['overall']['total'] += weld['total_length']
                stats['overall']['inspected'] += weld['inspected_length']
        
        for key in stats:
            if stats[key]['total'] > 0:
                stats[key]['percentage'] = (stats[key]['inspected'] / stats[key]['total']) * 100
        
        return stats
    
    def generate_length_report(self):
        """Generate detailed report"""
        stats = self.get_length_statistics()
        
        lines = []
        lines.append("=" * 70)
        lines.append("TANK INSPECTION - LENGTH-BASED PROGRESS")
        lines.append("=" * 70)
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append("SUMMARY:")
        lines.append(f"  Total:     {stats['overall']['total']:8.2f} m")
        lines.append(f"  Inspected: {stats['overall']['inspected']:8.2f} m")
        lines.append(f"  Remaining: {stats['overall']['total'] - stats['overall']['inspected']:8.2f} m")
        lines.append(f"  Progress:  {stats['overall']['percentage']:8.2f} %")
        lines.append("")
        
        progress = stats['overall']['percentage']
        bar_len = 50
        filled = int(bar_len * progress / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        lines.append(f"[{bar}] {progress:.1f}%")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    # Backward compatibility
    def mark_weld_inspected(self, weld_id):
        return self.mark_weld_complete(weld_id)
    
    def mark_welds_inspected(self, weld_ids):
        for weld_id in weld_ids:
            self.mark_weld_complete(weld_id)
    
    def get_completion_percentage(self):
        return self.get_length_statistics()['overall']['percentage']
    
    def get_total_welds(self):
        return sum(len(self.welds[t]) for t in ['horizontal', 'vertical', 'annular'])
    
    def get_inspected_welds(self):
        count = 0
        for weld_type in ['horizontal', 'vertical', 'annular']:
            count += sum(1 for w in self.welds[weld_type] if w['inspected'])
        return count
    
    def save_progress(self):
        """Save progress to JSON"""
        data = {
            'horizontal': self.welds['horizontal'],
            'vertical': self.welds['vertical'],
            'annular': self.welds['annular'],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(data, f, indent=2, cls=NumpyEncoder)
    
    def load_progress(self):
        """Load progress from JSON"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    
                for weld_type in ['horizontal', 'vertical', 'annular']:
                    saved_welds = data.get(weld_type, [])
                    for saved_weld in saved_welds:
                        for weld in self.welds[weld_type]:
                            if weld['id'] == saved_weld['id']:
                                weld['inspected_length'] = saved_weld.get('inspected_length', 0.0)
                                weld['inspected'] = saved_weld.get('inspected', False)
                                break
            except Exception as e:
                print(f"Note: Could not load previous progress ({e})")
                print("Starting fresh...")


# Quick test if run directly
if __name__ == "__main__":
    print("QUICK TEST")
    print("=" * 60)
    
    inspector = TankBottomInspection()
    
    print("Testing basic functions...")
    inspector.set_weld_length('H1', 15.0)
    inspector.set_weld_length('H10', 40.0)
    
    stats = inspector.get_length_statistics()
    print()
    print(f"Progress: {stats['overall']['inspected']:.1f}/{stats['overall']['total']:.1f}m")
    print(f"Percentage: {stats['overall']['percentage']:.1f}%")
    print()
    print("✓ Basic test passed!")
    print("=" * 60)
